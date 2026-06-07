"""
test_chunks.py — Chunk quality verification
Run before embedding. Checks for all common failure modes and
prints 5 random chunks for manual inspection.

Usage:
    python test_chunks.py

Exit code 0 = all checks passed, safe to embed.
Exit code 1 = problems found, fix before continuing.
"""

import json
import os
import random
import re
import sys

CHUNKS_PATH = "data/chunks/chunks.json"
SAMPLE_SIZE = 5
RANDOM_SEED = 42   # fixed seed so you get the same 5 chunks every run


# ── Load ───────────────────────────────────────────────────────────────────

def load_chunks(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run chunk.py first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        chunks = json.load(f)
    if not chunks:
        print(f"ERROR: {path} is empty.")
        sys.exit(1)
    return chunks


# ── Individual checks ──────────────────────────────────────────────────────

def check_empty(chunks: list[dict]) -> list[str]:
    """No chunk should have empty or whitespace-only text."""
    bad = [i for i, c in enumerate(chunks)
           if not c.get("text") or not c["text"].strip()]
    if bad:
        return [f"FAIL — {len(bad)} empty/whitespace chunks at indices: {bad[:10]}"]
    return ["PASS — no empty chunks"]


def check_html(chunks: list[dict]) -> list[str]:
    """No chunk should contain HTML tags or common entities."""
    html_pattern = re.compile(r"<[a-zA-Z/][^>]*>|&amp;|&nbsp;|&lt;|&gt;|&#\d+;")
    bad = [(i, re.findall(html_pattern, c["text"])[:3])
           for i, c in enumerate(chunks)
           if html_pattern.search(c["text"])]
    if bad:
        msgs = [f"FAIL — {len(bad)} chunks contain HTML artifacts"]
        for i, examples in bad[:3]:
            msgs.append(f"  chunk {i}: found {examples}")
        return msgs
    return ["PASS — no HTML artifacts"]


def check_size(chunks: list[dict]) -> list[str]:
    """Token counts should be reasonable (40–512)."""
    too_small = [i for i, c in enumerate(chunks) if c.get("token_count", 999) < 40]
    too_large = [i for i, c in enumerate(chunks) if c.get("token_count", 0) > 512]
    msgs = []
    if too_small:
        msgs.append(f"WARN — {len(too_small)} chunks under 40 tokens (may be too small to embed usefully): indices {too_small[:5]}")
    else:
        msgs.append("PASS — no chunks under 40 tokens")
    if too_large:
        msgs.append(f"FAIL — {len(too_large)} chunks over 512 tokens (will be truncated by all-MiniLM-L6-v2): indices {too_large[:5]}")
    else:
        msgs.append("PASS — no chunks over 512 tokens")
    return msgs


def check_metadata(chunks: list[dict]) -> list[str]:
    """Every chunk must have source_title, source_url, chunk_index."""
    required = ["text", "source_title", "source_url", "chunk_index", "token_count"]
    missing = []
    for i, c in enumerate(chunks):
        absent = [k for k in required if k not in c or c[k] is None]
        if absent:
            missing.append((i, absent))
    if missing:
        msgs = [f"FAIL — {len(missing)} chunks missing required fields"]
        for i, fields in missing[:3]:
            msgs.append(f"  chunk {i}: missing {fields}")
        return msgs
    return ["PASS — all chunks have required metadata"]


def check_source_diversity(chunks: list[dict]) -> list[str]:
    """Chunks should come from multiple source documents."""
    sources = set(c.get("source_title", "unknown") for c in chunks)
    if len(sources) < 3:
        return [f"WARN — only {len(sources)} distinct sources represented (expected 10)"]
    return [f"PASS — {len(sources)} distinct sources: {len(chunks)} total chunks"]


def check_duplicates(chunks: list[dict]) -> list[str]:
    """No two chunks should have identical text (sign of a bug in the splitter)."""
    texts = [c["text"] for c in chunks]
    seen, dupes = set(), 0
    for t in texts:
        if t in seen:
            dupes += 1
        seen.add(t)
    if dupes:
        return [f"WARN — {dupes} duplicate chunk texts found (overlapping chunks share text, but full duplicates suggest a bug)"]
    return ["PASS — no duplicate chunks"]


def check_fragment_starts(chunks: list[dict]) -> list[str]:
    """
    Mid-sentence starts are normal for sliding-window chunks (overlap means
    chunk N+1 starts inside chunk N). Flag only chunks that start with
    extremely short words that suggest a bad split, not just overlap.
    """
    # Only flag if the chunk starts with a lone punctuation or number
    bad = [i for i, c in enumerate(chunks)
           if re.match(r"^[^a-zA-Z]{0,3}\s", c.get("text", ""))]
    if bad:
        return [f"WARN — {len(bad)} chunks start with non-alphabetic characters: indices {bad[:5]}"]
    return ["PASS — all chunks start with readable text"]


# ── Main ───────────────────────────────────────────────────────────────────

def run_all_checks(chunks: list[dict]) -> bool:
    print("=" * 60)
    print("AUTOMATED CHECKS")
    print("=" * 60)

    all_checks = [
        check_empty,
        check_html,
        check_size,
        check_metadata,
        check_source_diversity,
        check_duplicates,
        check_fragment_starts,
    ]

    failed = False
    for check_fn in all_checks:
        results = check_fn(chunks)
        for msg in results:
            prefix = "  ✅" if msg.startswith("PASS") else \
                     "  ⚠️ " if msg.startswith("WARN") else \
                     "  ❌"
            print(f"{prefix} {msg}")
            if msg.startswith("FAIL"):
                failed = True

    return not failed


def print_random_samples(chunks: list[dict], n: int = SAMPLE_SIZE):
    random.seed(RANDOM_SEED)
    samples = random.sample(chunks, min(n, len(chunks)))

    print(f"\n{'=' * 60}")
    print(f"MANUAL INSPECTION — {n} random chunks")
    print(f"{'=' * 60}")
    print("For each chunk ask:")
    print("  1. Is it readable on its own?")
    print("  2. Could it answer a question without reading adjacent chunks?")
    print("  3. Does the source metadata look correct?")

    for i, c in enumerate(samples, 1):
        print(f"\n{'─' * 60}")
        print(f"CHUNK {i}/{n}")
        print(f"  Source : {c.get('source_title', 'MISSING')}")
        print(f"  Tokens : {c.get('token_count', '?')}  |  "
              f"Position: {c.get('chunk_index', '?')+1}/{c.get('chunk_total', '?')}  |  "
              f"Type: {c.get('segment_type', '?')}")
        print(f"{'─' * 60}")
        # Print full text, wrapped at 80 chars for readability
        text = c.get("text", "")
        for line in text.splitlines():
            # Wrap long lines
            while len(line) > 80:
                print(f"  {line[:80]}")
                line = line[80:]
            print(f"  {line}")

    print(f"\n{'─' * 60}")
    print("After reading: do all 5 chunks look substantive and self-contained?")
    print("If yes → commit and move to embed.py")
    print("If no  → note which chunk number looks bad and what's wrong")


def summary_stats(chunks: list[dict]):
    tokens = [c.get("token_count", 0) for c in chunks]
    sources = {}
    for c in chunks:
        t = c.get("source_title", "unknown")
        sources[t] = sources.get(t, 0) + 1

    print(f"\n{'=' * 60}")
    print("SUMMARY STATISTICS")
    print(f"{'=' * 60}")
    print(f"  Total chunks : {len(chunks)}")
    print(f"  Token range  : {min(tokens)} – {max(tokens)}")
    print(f"  Avg tokens   : {sum(tokens)/len(tokens):.0f}")
    print(f"  Sources      : {len(sources)}")
    print()
    print("  Chunks per document:")
    for title, count in sorted(sources.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"    {count:3d} {bar}  {title[:50]}")


if __name__ == "__main__":
    chunks = load_chunks(CHUNKS_PATH)
    summary_stats(chunks)
    passed = run_all_checks(chunks)
    print_random_samples(chunks)

    print(f"\n{'=' * 60}")
    if passed:
        print("✅ All checks passed. Safe to run embed.py.")
        print("   Don't forget to commit before moving to Milestone 4:")
        print("   git add data/chunks/chunks.json chunk.py clean.py")
        print('   git commit -m "milestone 3: clean and chunk 55 chunks"')
        sys.exit(0)
    else:
        print("❌ Some checks FAILED. Fix the issues above before embedding.")
        print("   Bad chunks cannot be fixed by tuning retrieval later.")
        sys.exit(1)