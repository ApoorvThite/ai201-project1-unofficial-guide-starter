"""
ingest_manual.py — Manual ingestion from local .txt or .json files
Reads whatever files you have in data/raw/ that are already JSON,
OR converts plain .txt files into the standard doc format.

Since you already have cleaned .json files in data/raw/, you likely
don't need to run this — just run chunk.py directly.

But if you need to re-import a .txt file, add it to MANUAL_SOURCES below.

Usage:
    python ingest_manual.py
"""

import json
import os
import re

RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)

# Only needed if you have new .txt files to convert.
# Your existing .json files in data/raw/ are already ready for chunk.py.
MANUAL_SOURCES = [
    # {"id": 11, "title": "New thread title", "url": "https://...", "file": "data/raw/new_thread.txt"},
]


def clean_text(text: str) -> str:
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    return text.strip()


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower())[:60].strip("_")


def ingest_manual():
    if not MANUAL_SOURCES:
        print("No manual sources configured.")
        print("Your data/raw/ JSON files are already ready — just run chunk.py.")
        return

    results = []
    for source in MANUAL_SOURCES:
        fpath = source["file"]
        if not os.path.exists(fpath):
            print(f"MISSING: {fpath}")
            continue

        with open(fpath, encoding="utf-8") as f:
            raw_text = f.read()

        doc = {
            "source_id":    source["id"],
            "source_title": source["title"],
            "source_url":   source["url"],
            "post_title":   source["title"],
            "post_body":    clean_text(raw_text),
            "author":       "manual_import",
            "subreddit":    "PennStateUniversity",
            "created_utc":  0,
            "score":        0,
            "comments":     [],
        }

        out = os.path.join(RAW_DIR, f"{source['id']:02d}_{slug(source['title'])}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        print(f"[{source['id']:02d}] ✓ {len(doc['post_body'].split())} words → {out}")
        results.append(doc)

    print(f"\nDone: {len(results)} files ingested.")


if __name__ == "__main__":
    ingest_manual()