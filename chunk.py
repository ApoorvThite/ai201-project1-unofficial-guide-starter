"""
chunk.py — Stage 2: Chunking

Spec (updated from planning.md):
  Chunk size : 400 tokens   ← reduced from 1000
  Overlap    : 80 tokens    ← reduced proportionally

WHY THE CHANGE:
  The embedding model (all-MiniLM-L6-v2) has a hard 512-token limit.
  Any chunk over 512 tokens gets silently truncated, meaning the tail
  of the chunk is never embedded and can never be retrieved.
  400 tokens gives comfortable headroom under the 512 limit.
  Overlap is kept at 20% (80/400) matching the original 200/1000 ratio.

Output:
  data/chunks/chunks.json
  data/chunks/_stats.json
"""

import json, os, re, sys

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text): return len(_enc.encode(text))
    def tokenize(text):     return _enc.encode(text)
    def detokenize(tokens): return _enc.decode(tokens)
    TOKENIZER = "tiktoken/cl100k_base"
except ImportError:
    print("WARNING: tiktoken not found — using word approximation (tokens ≈ words/0.75)")
    def count_tokens(text): return int(len(text.split()) / 0.75)
    def tokenize(text):     return text.split()
    def detokenize(tokens): return " ".join(tokens)
    TOKENIZER = "word-approx"

RAW_DIR       = "data/raw"
CHUNK_DIR     = "data/chunks"
CHUNK_SIZE    = 400    # tokens — fits within all-MiniLM-L6-v2's 512-token limit
CHUNK_OVERLAP = 80     # 20% overlap, same ratio as original spec
MIN_CHUNK     = 40     # discard tiny trailing fragments

os.makedirs(CHUNK_DIR, exist_ok=True)


def sliding_window(text: str) -> list[str]:
    tokens = tokenize(text)
    total  = len(tokens)
    if total < MIN_CHUNK:
        return []
    if total <= CHUNK_SIZE:
        return [text.strip()]
    chunks, start = [], 0
    while start < total:
        end = min(start + CHUNK_SIZE, total)
        chunk_str = detokenize(tokens[start:end]).strip()
        if (end - start) >= MIN_CHUNK:
            chunks.append(chunk_str)
        if end == total:
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def doc_to_segments(doc: dict) -> list[dict]:
    segments = []
    post_text = f"{doc['post_title']}\n\n{doc['post_body']}".strip()
    if post_text:
        segments.append({"text": post_text, "segment_type": "post",
                         "author": doc.get("author",""), "score": doc.get("score",0)})
    threads, top_level = {}, []
    for i, c in enumerate(doc.get("comments", [])):
        if c["depth"] == 0:
            threads[i] = [c]; top_level.append(i)
        elif top_level:
            threads[top_level[-1]].append(c)
    for idx in top_level:
        parts = [f"{'  '*c['depth']}u/{c['author']}: {c['body']}" for c in threads[idx]]
        thread_text = "\n\n".join(parts).strip()
        if thread_text:
            segments.append({"text": thread_text, "segment_type": "comment_thread",
                              "author": threads[idx][0]["author"], "score": threads[idx][0]["score"]})
    return segments


def chunk_all_documents():
    raw_files = sorted(f for f in os.listdir(RAW_DIR)
                       if f.endswith(".json") and not f.startswith("_"))
    if not raw_files:
        print(f"No JSON files in {RAW_DIR}/"); sys.exit(1)

    print(f"Tokenizer  : {TOKENIZER}")
    print(f"Chunk size : {CHUNK_SIZE} tokens  |  Overlap: {CHUNK_OVERLAP} tokens")
    print(f"Model limit: 512 tokens (all-MiniLM-L6-v2)")
    print(f"Documents  : {len(raw_files)}\n")

    all_chunks, stats = [], []

    for fname in raw_files:
        with open(os.path.join(RAW_DIR, fname), encoding="utf-8") as f:
            doc = json.load(f)

        segments   = doc_to_segments(doc)
        doc_chunks = []

        for seg in segments:
            windows = sliding_window(seg["text"])
            for i, w in enumerate(windows):
                tok = count_tokens(w)
                doc_chunks.append({
                    "text":           w,
                    "token_count":    tok,
                    "source_id":      doc["source_id"],
                    "source_title":   doc["source_title"],
                    "source_url":     doc["source_url"],
                    "subreddit":      doc.get("subreddit", "PennStateUniversity"),
                    "segment_type":   seg["segment_type"],
                    "segment_author": seg["author"],
                    "segment_score":  seg["score"],
                    "chunk_index":    i,
                    "chunk_total":    len(windows),
                    "over_limit":     tok > 512,   # flag any that still exceed model limit
                })

        n   = len(doc_chunks)
        avg = sum(c["token_count"] for c in doc_chunks) / n if n else 0
        over = sum(1 for c in doc_chunks if c["over_limit"])
        flag = f"  ⚠️  {over} over 512!" if over else ""
        print(f"  {fname}")
        print(f"    segments={len(segments)}  chunks={n}  avg_tokens={avg:.0f}{flag}")
        all_chunks.extend(doc_chunks)
        stats.append({"filename": fname, "source_title": doc["source_title"],
                      "n_chunks": n, "avg_tokens": round(avg,1), "over_limit": over})

    chunks_path = os.path.join(CHUNK_DIR, "chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    with open(os.path.join(CHUNK_DIR, "_stats.json"), "w") as f:
        json.dump({"tokenizer": TOKENIZER, "chunk_size": CHUNK_SIZE,
                   "chunk_overlap": CHUNK_OVERLAP, "model_limit": 512,
                   "total_chunks": len(all_chunks), "per_document": stats}, f, indent=2)

    over_total = sum(1 for c in all_chunks if c["over_limit"])
    print(f"\n{'='*50}")
    print(f"Total chunks : {len(all_chunks)}")
    print(f"Over 512 tok : {over_total}  {'✅ none' if over_total==0 else '⚠️  check these'}")
    print(f"Saved to     : {chunks_path}")

    # Spot-check
    print(f"\n--- Spot-check: chunk 0 ---")
    c = all_chunks[0]
    print(f"tokens : {c['token_count']}  (limit: 512)")
    print(f"source : {c['source_title']}")
    print(f"text   :\n{c['text'][:400]}\n...")
    return all_chunks

if __name__ == "__main__":
    chunk_all_documents()