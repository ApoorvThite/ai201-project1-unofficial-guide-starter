"""
retrieve.py — Stage 4: Retrieval
=================================
Pipeline position:
  ChromaDB → [retrieve.py] → top-k chunks → generate.py

What this script does:
  1. Connects to the persisted ChromaDB vector store built by embed.py
  2. Exposes a retrieve() function: query string → top-k chunks
  3. Runs your 5 evaluation questions from planning.md as a smoke test

Usage:
    python retrieve.py                  # runs eval questions
    python retrieve.py "your question"  # retrieves for a custom query

How retrieval works (plain English):
  1. Your query string is embedded into a 384-dim vector by the same
     model used in embed.py (all-MiniLM-L6-v2).
  2. ChromaDB computes the cosine similarity between the query vector
     and every stored chunk vector.
  3. The top-k most similar chunks are returned — these are the chunks
     most likely to contain a relevant answer.
  4. Those chunks get passed to the LLM in generate.py as context.
"""

import sys
import os

try:
    import chromadb
except ImportError:
    print("ERROR: pip install chromadb")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: pip install sentence-transformers")
    sys.exit(1)

# ── Config (must match embed.py) ───────────────────────────────────────────
CHROMA_DIR      = "data/chroma"
COLLECTION_NAME = "psu_housing"
EMBED_MODEL     = "all-MiniLM-L6-v2"
TOP_K           = 5   # number of chunks to retrieve per query (from planning.md)

# Evaluation questions from planning.md
EVAL_QUESTIONS = [
    "What strategies do Penn State students recommend for commuting in harsh winter weather?",
    "Which specific apartment complexes do students warn others to avoid in State College?",
    "What do students say causes traffic backups and CATA bus delays near campus?",
    "What are the most common misconceptions about parking permits at Penn State?",
    "What specific maintenance or management issues do students report about State College landlords?",
]


# ── Core retrieval function ────────────────────────────────────────────────

class Retriever:
    """
    Wraps ChromaDB + SentenceTransformer into a simple retrieve() call.

    WHY a class instead of a bare function?
    Loading the model and connecting to ChromaDB takes ~1-2 seconds.
    A class lets us do that once at __init__ time and reuse the loaded
    objects for multiple queries — important when generate.py calls
    retrieve() in a loop or serves multiple user requests.
    """

    def __init__(self,
                 chroma_dir: str = CHROMA_DIR,
                 collection_name: str = COLLECTION_NAME,
                 model_name: str = EMBED_MODEL):

        if not os.path.exists(chroma_dir):
            print(f"ERROR: {chroma_dir} not found. Run embed.py first.")
            sys.exit(1)

        print(f"Loading embedding model '{model_name}'...")
        self.model = SentenceTransformer(model_name)

        print(f"Connecting to ChromaDB at '{chroma_dir}'...")
        self.client     = chromadb.PersistentClient(path=chroma_dir)
        self.collection = self.client.get_collection(name=collection_name)

        count = self.collection.count()
        print(f"Collection '{collection_name}' — {count} chunks indexed\n")

    def retrieve(self,
                 query: str,
                 k: int = TOP_K,
                 min_similarity: float = 0.0) -> list[dict]:
        """
        Embed a query string and return the top-k most similar chunks.

        Parameters
        ----------
        query           : the user's question
        k               : how many chunks to return (default: TOP_K from planning.md)
        min_similarity  : filter out chunks below this cosine similarity (0.0 = no filter)

        Returns
        -------
        List of dicts, each with keys:
          text          — the chunk text to pass to the LLM
          similarity    — cosine similarity score (0–1, higher = more relevant)
          source_title  — which Reddit thread this came from
          source_url    — link back to original post
          rank          — position in results (1 = most relevant)
          + all other metadata fields stored in embed.py

        WHY include=["documents", "metadatas", "distances"]?
        ChromaDB returns only what you ask for.
        - "documents"  → the raw chunk text
        - "metadatas"  → our source_title, source_url, etc.
        - "distances"  → cosine DISTANCE (0=identical, 2=opposite)
          We convert: similarity = 1 - distance
        """
        query_embedding = self.model.encode(query, convert_to_numpy=True).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        # Unpack ChromaDB's nested list format
        # results["documents"] = [[chunk1, chunk2, ...]]  ← note double list
        # The outer list is per query (we only send one query at a time)
        chunks_out = []
        for rank, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ), start=1):
            similarity = 1.0 - dist   # convert cosine distance → similarity

            if similarity < min_similarity:
                continue

            chunks_out.append({
                "rank":          rank,
                "text":          doc,
                "similarity":    round(similarity, 4),
                "source_title":  meta.get("source_title", ""),
                "source_url":    meta.get("source_url", ""),
                "source_id":     meta.get("source_id", ""),
                "segment_type":  meta.get("segment_type", ""),
                "token_count":   meta.get("token_count", 0),
                "chunk_index":   meta.get("chunk_index", 0),
                "chunk_total":   meta.get("chunk_total", 0),
            })

        return chunks_out


# ── Display helper ─────────────────────────────────────────────────────────

def print_results(query: str, results: list[dict]):
    print(f"\n{'='*65}")
    print(f"QUERY: {query}")
    print(f"{'='*65}")

    if not results:
        print("  No results returned.")
        return

    for r in results:
        print(f"\n  Rank {r['rank']}  |  similarity={r['similarity']:.4f}  "
              f"|  tokens={r['token_count']}")
        print(f"  Source: {r['source_title']}")
        print(f"  {'─'*59}")
        # Print first 300 chars of the chunk
        preview = r['text'][:300].replace('\n', ' ')
        print(f"  {preview}...")


# ── Evaluation run ─────────────────────────────────────────────────────────

def run_eval(retriever: Retriever):
    """
    Run all 5 evaluation questions from planning.md.
    For each, check:
      - Is the top result relevant to the question?
      - Is the similarity score reasonable (>0.3 is a decent signal)?
      - Does the source title make sense for this question?
    """
    print("\n" + "="*65)
    print("EVALUATION — 5 questions from planning.md")
    print("="*65)
    print("For each result, ask:")
    print("  • Is the top chunk actually relevant to the question?")
    print("  • Does the source title make sense?")
    print("  • Is similarity > 0.3? (below that = weak match)")

    for q in EVAL_QUESTIONS:
        results = retriever.retrieve(q, k=TOP_K)
        print_results(q, results)

    print(f"\n{'='*65}")
    print("Retrieval smoke test complete.")
    print("If top results look relevant → proceed to generate.py")
    print("If results look wrong → check embed.py ran without errors")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    retriever = Retriever()

    if len(sys.argv) > 1:
        # Custom query from command line
        query = " ".join(sys.argv[1:])
        results = retriever.retrieve(query)
        print_results(query, results)
    else:
        # Default: run evaluation questions
        run_eval(retriever)


if __name__ == "__main__":
    main()