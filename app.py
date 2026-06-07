"""
app.py — Gradio Interface
==========================
Wraps generate.py in a web UI. Run this to interact with your
RAG system through a browser instead of the command line.

Usage:
    pip install gradio
    python app.py
    # Opens at http://localhost:7860
"""

import os, sys
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # suppress a noisy warning

try:
    import gradio as gr
except ImportError:
    print("ERROR: pip install gradio")
    sys.exit(1)

try:
    from groq import Groq
except ImportError:
    print("ERROR: pip install groq")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(__file__))
from retrieve  import Retriever
from generate  import generate

# ── Load once at startup (not on every query) ──────────────────────────────
print("Loading retriever and LLM client...")
retriever = Retriever()
client    = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
print("Ready.\n")


# ── Core query function called by Gradio ──────────────────────────────────

def answer_question(query: str) -> tuple[str, str, str]:
    """
    Takes user query, returns (answer, sources, debug_info).
    Gradio maps these to the three output components.
    """
    if not query.strip():
        return "Please enter a question.", "", ""

    if not os.getenv("GROQ_API_KEY"):
        return ("ERROR: GROQ_API_KEY not set in .env file.\n"
                "Get a free key at https://console.groq.com"), "", ""

    result = generate(query, retriever, client, verbose=False)

    # Debug info: show which chunks were retrieved and their similarity
    debug_lines = []
    for c in result["chunks"]:
        debug_lines.append(
            f"Rank {c['rank']} | sim={c['similarity']:.3f} | "
            f"{c['source_title'][:45]}\n"
            f"  {c['text'][:120].replace(chr(10), ' ')}..."
        )
    debug_info = "\n\n".join(debug_lines)

    return result["answer"], result["sources"], debug_info


# ── Example questions (shown in the UI) ───────────────────────────────────

EXAMPLES = [
    "What apartments should I avoid in State College?",
    "How do students survive the cold winter walking to campus?",
    "What are the rules for parking on campus at Penn State?",
    "How hard is it to find fall-only housing near Penn State?",
    "What do students say about CATA bus delays?",
    "What are my rights if my landlord changes my rent after I signed?",
]


# ── Build Gradio UI ────────────────────────────────────────────────────────

def build_interface() -> gr.Blocks:
    with gr.Blocks(title="PSU Off-Campus Housing Guide", theme=gr.themes.Soft()) as demo:

        gr.Markdown("""
        # 🦁 PSU Off-Campus Housing Guide
        **Ask questions about off-campus housing, landlords, parking, and commuting in State College.**
        Answers are grounded in real student experiences from r/PennStateUniversity.
        """)

        with gr.Row():
            with gr.Column(scale=3):
                query_box = gr.Textbox(
                    label="Your question",
                    placeholder="e.g. What apartments should I avoid in State College?",
                    lines=2,
                )
                submit_btn = gr.Button("Ask", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("**Example questions:**")
                for ex in EXAMPLES:
                    gr.Button(ex, size="sm").click(
                        fn=lambda q=ex: q,
                        outputs=query_box,
                    )

        answer_box = gr.Textbox(
            label="Answer",
            lines=6,
            interactive=False,
        )

        sources_box = gr.Textbox(
            label="Sources (from r/PennStateUniversity)",
            lines=4,
            interactive=False,
        )

        with gr.Accordion("🔍 Retrieved chunks (debug)", open=False):
            debug_box = gr.Textbox(
                label="Top-5 retrieved chunks",
                lines=12,
                interactive=False,
            )

        # Wire up submit button and Enter key
        submit_btn.click(
            fn=answer_question,
            inputs=query_box,
            outputs=[answer_box, sources_box, debug_box],
        )
        query_box.submit(
            fn=answer_question,
            inputs=query_box,
            outputs=[answer_box, sources_box, debug_box],
        )

        gr.Markdown("""
        ---
        *Built with Reddit posts from r/PennStateUniversity · 
        Powered by all-MiniLM-L6-v2 + Llama 3.3 70B via Groq*
        """)

    return demo


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,       # set share=True to get a public URL
        show_error=True,
    )