"""
clean.py — Document cleaning pass
Reads every JSON in data/raw/, applies a cleaning pipeline,
and overwrites in place. Run this BEFORE chunk.py.

What it removes:
  - "Discussion" / "Question" / "Advice" Reddit flair labels
    that appear as a lone word on their own line
  - URLs (standalone lines that are just links)
  - HTML entities (&amp; &nbsp; &gt; &lt; etc.)
  - Excessive whitespace and blank lines
  - Unicode junk (zero-width spaces, non-breaking spaces)

What it keeps:
  - Post title
  - All substantive post body and comment text
  - Apartment/landlord names, specific advice, opinions

After running: prints a full preview of one doc so you can
visually confirm the output looks right before chunking.
"""

import json
import os
import re

RAW_DIR = "data/raw"

# Reddit flair labels that appear as standalone lines after the title
REDDIT_FLAIR = {
    "Discussion", "Question", "Advice", "Rant", "Humor",
    "News", "Help", "Megathread", "Announcement", "Serious",
}

# HTML entities to decode
HTML_ENTITIES = {
    "&amp;":  "&",
    "&nbsp;": " ",
    "&gt;":   ">",
    "&lt;":   "<",
    "&quot;": '"',
    "&#39;":  "'",
    "&apos;": "'",
    "&#x27;": "'",
    "&#x2F;": "/",
}


def clean_document(text: str) -> str:
    # 1. Decode HTML entities
    for entity, replacement in HTML_ENTITIES.items():
        text = text.replace(entity, replacement)

    # 2. Remove any remaining &#NNN; or &#xHHH; numeric entities
    text = re.sub(r"&#x?[0-9a-fA-F]+;", "", text)

    # 3. Remove standalone URLs on their own line
    text = re.sub(r"^\s*https?://\S+\s*$", "", text, flags=re.MULTILINE)

    # 4. Remove Reddit flair labels that appear as a lone word on a line
    #    (e.g. a line containing only "Discussion" or "Question")
    flair_pattern = r"^\s*(" + "|".join(re.escape(f) for f in REDDIT_FLAIR) + r")\s*$"
    text = re.sub(flair_pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

    # 5. Remove Unicode junk characters
    text = re.sub(r"[\u200b\u200c\u200d\u00ad\ufeff]", "", text)  # zero-width, soft-hyphen, BOM
    text = text.replace("\u00a0", " ")   # non-breaking space → regular space
    text = text.replace("\u2019", "'").replace("\u2018", "'")  # smart quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')

    # 6. Remove lines that are only punctuation / emoji residue with no words
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Keep the line if it has at least one alphabetic character
        if stripped and re.search(r"[a-zA-Z]", stripped):
            lines.append(stripped)
        elif not stripped:
            lines.append("")  # preserve intentional blank lines

    text = "\n".join(lines)

    # 7. Collapse 3+ consecutive blank lines → single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_all():
    files = sorted(
        f for f in os.listdir(RAW_DIR)
        if f.endswith(".json") and not f.startswith("_")
    )

    if not files:
        print(f"No JSON files found in {RAW_DIR}/")
        return

    print(f"Cleaning {len(files)} documents...\n")

    for fname in files:
        fpath = os.path.join(RAW_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            doc = json.load(f)

        original_len = len(doc["post_body"])
        doc["post_body"] = clean_document(doc["post_body"])
        cleaned_len = len(doc["post_body"])
        removed = original_len - cleaned_len

        # Also clean comment bodies if present
        for comment in doc.get("comments", []):
            comment["body"] = clean_document(comment["body"])

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)

        print(f"  {fname}")
        print(f"    {original_len:,} chars → {cleaned_len:,} chars  (-{removed:,} removed)")

    # ── Visual spot-check: print one full document ──────────────────────────
    print("\n" + "="*70)
    print("SPOT CHECK — full text of: 05_i_work_in_parking_for_psu_please_read_this.json")
    print("="*70)
    spot_path = os.path.join(RAW_DIR, "i work in parking for psu.json")
    if os.path.exists(spot_path):
        with open(spot_path, encoding="utf-8") as f:
            doc = json.load(f)
        print(doc["post_body"])
    else:
        # Fall back to first available file
        first = os.path.join(RAW_DIR, files[0])
        with open(first, encoding="utf-8") as f:
            doc = json.load(f)
        print(f"(showing {files[0]} instead)")
        print(doc["post_body"])

    print("\n" + "="*70)
    print("If you see any nav text, HTML, or junk above — edit clean_document()")
    print("and re-run before proceeding to chunk.py.")


if __name__ == "__main__":
    clean_all()