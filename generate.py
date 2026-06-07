"""
generate.py — Stage 5: Generation
===================================
Pipeline position:
  User query → retrieve.py → [generate.py] → grounded answer + sources

What this script does:
  1. Takes a user question
  2. Retrieves top-5 relevant chunks from ChromaDB (via Retriever)
  3. Builds a grounded prompt — LLM is explicitly told to answer
     ONLY from the provided context, not from general knowledge
  4. Calls Groq's llama-3.3-70b-versatile
  5. Returns the answer + programmatic source attribution

Grounding strategy:
  - System prompt FORBIDS the LLM from using outside knowledge
  - Each chunk is labelled [Source N: <title>] in the prompt
  - LLM is instructed to cite [Source N] inline in its answer
  - Source list is ALSO appended programmatically after generation
    so attribution is guaranteed even if the LLM forgets to cite

Usage:
    pip install groq python-dotenv
    # Add to .env:  GROQ_API_KEY=your_key_here
    python generate.py
    python generate.py "your question here"
"""

import os, sys, json

try:
    from groq import Groq
except ImportError:
    print("ERROR: pip install groq")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # .env values set manually as env vars is fine too

# ── Import retriever from retrieve.py ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
try:
    from retrieve import Retriever
except ImportError:
    print("ERROR: retrieve.py not found in the same folder.")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────
GROQ_MODEL  = "llama-3.3-70b-versatile"
TOP_K       = 5
MAX_TOKENS  = 512


# ── Prompt builder ─────────────────────────────────────────────────────────

def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    """
    Build a system prompt and user message that enforce grounding.

    Returns (system_prompt, user_message).

    WHY two separate messages?
    The system prompt sets hard rules the LLM must follow for the
    entire conversation. The user message contains the actual context
    + question. Separating them makes the grounding constraint harder
    for the model to ignore than if everything were in one message.

    WHY label each chunk [Source N]?
    So the LLM can cite specific sources inline ("according to [Source 2]")
    rather than making up generic attributions. We then cross-reference
    those labels against our chunk metadata to build the source list.
    """

    # ── System prompt: grounding rules ────────────────────────────────────
    system_prompt = """You are a helpful assistant for Penn State University students looking for information about off-campus housing, landlords, parking, and commuting in State College, PA.

RULES YOU MUST FOLLOW:
1. Answer ONLY using information from the provided sources below.
2. Do NOT use your general training knowledge about housing, landlords, or State College.
3. If the sources don't contain enough information to answer the question, say exactly: "I don't have enough information on that in my sources."
4. Cite your sources inline using [Source N] notation when you use information from them.
5. Be specific — quote apartment names, specific advice, or exact details when they appear in the sources.
6. Keep your answer focused and under 200 words."""

    # ── User message: context + question ──────────────────────────────────
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {i}: {chunk['source_title']}]\n{chunk['text']}"
        )

    context_str  = "\n\n---\n\n".join(context_blocks)
    user_message = f"""Here are the relevant sources:

{context_str}

---

Question: {query}

Answer (cite sources inline using [Source N]):"""

    return system_prompt, user_message


# ── Source attribution builder ─────────────────────────────────────────────

def build_source_list(chunks: list[dict]) -> str:
    """
    Build a programmatic source list from chunk metadata.

    WHY programmatic rather than relying on the LLM?
    The LLM might forget to list sources, hallucinate a source title,
    or list sources it didn't actually use. By building the list from
    the retrieved chunk metadata directly, attribution is always accurate
    and always present — regardless of what the LLM generates.
    """
    seen   = {}
    lines  = []
    for i, chunk in enumerate(chunks, start=1):
        title = chunk["source_title"]
        url   = chunk["source_url"]
        if title not in seen:
            seen[title] = i
            lines.append(f"  [{i}] {title}\n      {url}")
    return "\n".join(lines)


# ── Main generation function ───────────────────────────────────────────────

def generate(query: str,
             retriever: Retriever,
             client: Groq,
             verbose: bool = True) -> dict:
    """
    Full RAG pipeline: query → retrieve → generate → return.

    Returns dict with:
      answer       — LLM's grounded response
      sources      — programmatic source list string
      chunks       — the raw retrieved chunks (for debugging)
      query        — the original query
    """

    # 1. Retrieve
    chunks = retriever.retrieve(query, k=TOP_K)
    if not chunks:
        return {
            "answer":  "I don't have enough information on that in my sources.",
            "sources": "",
            "chunks":  [],
            "query":   query,
        }

    # 2. Build prompt
    system_prompt, user_message = build_prompt(query, chunks)

    # 3. Call Groq
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_message},
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.2,   # low temperature = more factual, less creative
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        return {
            "answer":  f"Error calling Groq API: {e}",
            "sources": "",
            "chunks":  chunks,
            "query":   query,
        }

    # 4. Build programmatic source list
    source_list = build_source_list(chunks)

    if verbose:
        print(f"\n{'='*65}")
        print(f"QUERY: {query}")
        print(f"{'='*65}")
        print(f"\nANSWER:\n{answer}")
        print(f"\nSOURCES:\n{source_list}")
        print(f"\n(retrieved {len(chunks)} chunks, "
              f"top similarity: {chunks[0]['similarity']:.3f})")

    return {
        "answer":  answer,
        "sources": source_list,
        "chunks":  chunks,
        "query":   query,
    }


# ── Evaluation run ─────────────────────────────────────────────────────────

EVAL_QUESTIONS = [
    "What strategies do Penn State students recommend for commuting in harsh winter weather?",
    "Which specific apartment complexes do students warn others to avoid in State College?",
    "What do students say causes traffic backups and CATA bus delays near campus?",
    "What are the most common misconceptions about parking permits at Penn State?",
    "What specific maintenance or management issues do students report about State College landlords?",
]


def run_eval(retriever: Retriever, client: Groq):
    print("Running evaluation on 5 planning.md questions...\n")
    results = []
    for q in EVAL_QUESTIONS:
        r = generate(q, retriever, client, verbose=True)
        results.append(r)
    return results


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.")
        print("  1. Get a free key at https://console.groq.com")
        print("  2. Add to .env:  GROQ_API_KEY=your_key_here")
        sys.exit(1)

    client    = Groq(api_key=api_key)
    retriever = Retriever()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        generate(query, retriever, client, verbose=True)
    else:
        run_eval(retriever, client)


if __name__ == "__main__":
    main()