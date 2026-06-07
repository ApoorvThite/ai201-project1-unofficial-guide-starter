"""
embed.py — Stage 3: Embedding + Vector Store
============================================
Pipeline position:
  chunks.json → [embed.py] → ChromaDB → retrieve.py

What this script does:
  1. Loads all 55 chunks from data/chunks/chunks.json
  2. Embeds each chunk's text using all-MiniLM-L6-v2
     (384-dimensional vectors, max 512 tokens)
  3. Stores vectors + metadata in a local ChromaDB collection
     persisted to data/chroma/

Run once to build the vector store. Re-run to rebuild from scratch.

Usage:
    pip install sentence-transformers chromadb
    python embed.py
"""

import json
import os
import sys
import time

# ── Dependency checks with helpful messages ────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed.")
    print("       pip install sentence-transformers")
    sys.exit(1)

try:
    import chromadb
except ImportError:
    print("ERROR: chromadb not installed.")
    print("       pip install chromadb")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────
CHUNKS_PATH    = "data/chunks/chunks.json"
CHROMA_DIR     = "data/chroma"
COLLECTION_NAME = "psu_housing"
EMBED_MODEL    = "all-MiniLM-L6-v2"
BATCH_SIZE     = 32   # embed this many chunks at once (fits in memory)


# ── Helpers ────────────────────────────────────────────────────────────────

def load_chunks(path: str) -> list[dict]:
    """Load chunks.json and validate it has the fields we need."""
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run chunk.py first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks from {path}")
    return chunks


def build_chroma_client(persist_dir: str) -> chromadb.PersistentClient:
    """
    Create a ChromaDB client that persists to disk.

    WHY PersistentClient?
    The default in-memory client loses all data when the script exits.
    PersistentClient writes a SQLite database to persist_dir so the
    vectors survive between runs — retrieve.py can load them without
    re-embedding.
    """
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)
    return client


def get_or_create_collection(client: chromadb.PersistentClient,
                              name: str) -> chromadb.Collection:
    """
    Delete any existing collection with this name and create a fresh one.

    WHY delete first?
    If you re-run embed.py after changing your chunks, you want a clean
    slate. ChromaDB will error if you try to add a document ID that
    already exists in the collection.

    WHY no embedding_function argument?
    We embed manually with SentenceTransformer and pass the raw vectors
    to ChromaDB ourselves (embeddings= parameter in collection.add).
    This gives us full control over batching and lets us use any model.
    If you passed an embedding_function, ChromaDB would embed for you,
    but you'd lose visibility into what's happening.
    """
    try:
        client.delete_collection(name)
        print(f"Deleted existing collection '{name}'")
    except Exception:
        pass  # collection didn't exist yet — that's fine

    collection = client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},  # use cosine similarity (not L2)
    )
    print(f"Created collection '{name}'")
    return collection


def chunks_to_chroma_format(chunks: list[dict]) -> tuple[list, list, list]:
    """
    Convert our chunk dicts into the three parallel lists ChromaDB expects:
      ids        — unique string ID per document
      documents  — the raw text (ChromaDB stores this for you to retrieve)
      metadatas  — dict of filterable fields (no nested dicts or lists allowed)

    WHY store metadata?
    At retrieval time we get back the metadata alongside the text, so we
    can tell the user "this answer comes from the parking PSA post" rather
    than just returning anonymous text.

    ChromaDB metadata restriction: values must be str, int, float, or bool.
    Lists and nested dicts are not allowed — that's why we store
    chunk_index and chunk_total as ints, not as "3/7".
    """
    ids, documents, metadatas = [], [], []

    for i, chunk in enumerate(chunks):
        # Build a unique ID: source_id + chunk position
        chunk_id = f"src{chunk['source_id']}_chunk{chunk['chunk_index']}_{i}"

        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "source_id":      int(chunk["source_id"]),
            "source_title":   str(chunk["source_title"]),
            "source_url":     str(chunk["source_url"]),
            "subreddit":      str(chunk.get("subreddit", "PennStateUniversity")),
            "segment_type":   str(chunk.get("segment_type", "post")),
            "segment_author": str(chunk.get("segment_author", "")),
            "segment_score":  int(chunk.get("segment_score", 0)),
            "chunk_index":    int(chunk["chunk_index"]),
            "chunk_total":    int(chunk["chunk_total"]),
            "token_count":    int(chunk.get("token_count", 0)),
        })

    return ids, documents, metadatas


def embed_and_store(chunks: list[dict],
                    collection: chromadb.Collection,
                    model: SentenceTransformer):
    """
    Embed all chunks in batches and upsert into ChromaDB.

    WHY batch?
    SentenceTransformer.encode() is much faster when given a list of
    texts rather than one at a time — it parallelises across your CPU/GPU.
    BATCH_SIZE=32 is a safe default; increase to 64 if you have more RAM.

    WHAT does collection.add() do?
    It stores three things per chunk:
      - The embedding vector (for similarity search)
      - The raw document text (returned at query time)
      - The metadata dict (filterable, also returned at query time)
    ChromaDB links these by the ID — so ids[i], embeddings[i],
    documents[i], and metadatas[i] must all refer to the same chunk.
    """
    ids, documents, metadatas = chunks_to_chroma_format(chunks)
    total = len(chunks)

    print(f"\nEmbedding {total} chunks with '{EMBED_MODEL}' in batches of {BATCH_SIZE}...")
    t0 = time.time()

    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch_texts = documents[start:end]

        # encode() returns a numpy array of shape (batch_size, 384)
        # convert_to_numpy=True ensures ChromaDB can serialise the vectors
        batch_embeddings = model.encode(
            batch_texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()   # ChromaDB wants a plain Python list of lists

        collection.add(
            ids=ids[start:end],
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=metadatas[start:end],
        )

        elapsed = time.time() - t0
        print(f"  [{end:3d}/{total}] embedded  ({elapsed:.1f}s)")

    print(f"\nDone. {total} chunks stored in '{COLLECTION_NAME}'")
    print(f"Vector store: {CHROMA_DIR}/")


def verify_collection(collection: chromadb.Collection):
    """
    Quick sanity check: query the collection with a test question
    and print the top result. If this returns sensible text, the
    vector store is working correctly.
    """
    print("\n── Verification query ────────────────────────────────────────")
    print("Query: 'what apartments should I avoid in State College?'")

    results = collection.query(
        query_texts=["what apartments should I avoid in State College?"],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    if results["documents"] and results["documents"][0]:
        doc      = results["documents"][0][0]
        meta     = results["metadatas"][0][0]
        distance = results["distances"][0][0]
        score    = 1 - distance   # cosine distance → cosine similarity

        print(f"\nTop result (similarity={score:.3f}):")
        print(f"  Source : {meta['source_title']}")
        print(f"  Tokens : {meta['token_count']}")
        print(f"  Text   : {doc[:300]}...")
    else:
        print("WARNING: no results returned — something may have gone wrong.")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    # 1. Load chunks
    chunks = load_chunks(CHUNKS_PATH)

    # 2. Load embedding model
    #    First run downloads ~90MB to ~/.cache/huggingface/
    #    Subsequent runs load from cache — fast.
    print(f"\nLoading embedding model '{EMBED_MODEL}'...")
    model = SentenceTransformer(EMBED_MODEL)
    print(f"Model loaded. Output dimension: {model.get_sentence_embedding_dimension()}")

    # 3. Set up ChromaDB
    client     = build_chroma_client(CHROMA_DIR)
    collection = get_or_create_collection(client, COLLECTION_NAME)

    # 4. Embed and store
    embed_and_store(chunks, collection, model)

    # 5. Verify it works
    verify_collection(collection)

    print("\n✅ Vector store ready.")
    print("   Next step: python retrieve.py")


if __name__ == "__main__":
    main()