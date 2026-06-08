# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

Penn State Housing Guide - Useful because it provides insights into the experiences of Penn State students living in different housing options, including apartments and dorms. It helps potential students understand the pros and cons of each housing option, such as cost, amenities, and community. It's hard to find through official channels because official sources may not provide detailed personal experiences and reviews from students. Sites like RateMyProfessors exist for courses, but no equivalent exists for landlords or apartments. Students posting on r/PennStateUniversity share candid, experience-based knowledge — specific apartment names to avoid, exact parking garage rules, layering strategies for -10°F wind chill, that no official source provides.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | PSA: Avoid Tremont, The Bryn & The Pointe | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1812345/psa_avoid_tremont_the_bryn_the_pointe/ |
| 2 | The landlord issue in State College should be studied | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1ni0lot/ |
| 3 | What's up with traffic/CATA this sem? | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1n6ls91/ |
| 4 | How tf do people walk in bitterly cold weather? | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1qzfs2p/ |
| 5 | I work in parking for PSU — please read this | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1mjjbkn/ |
| 6 | Fall Only Housing | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/16jgrcu/ |
| 7 | Reminder to Rate your Landlords and Professors | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1te4l4y/ |
| 8 | Locked apartment buildings and delivery drivers | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1ov8oim/ |
| 9 | Moving up from the midwest — landlords are leeches | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/ou3v1i/ |
| 10 | Borough Council — college students belong in State College | Reddit Post | https://www.reddit.com/r/PennStateUniversity/comments/1ni0lot/ |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 400 tokens

**Overlap:** 80 tokens (20% of chunk size)

**Why these choices fit your documents:** 
Reddit threads are conversational and dense, individual comments often contain a complete thought in 100–300 words. The original spec called for 1,000-token chunks, but during implementation I discovered that the embedding model (all-MiniLM-L6-v2) has a hard 512-token limit. Chunks above 512 tokens get silently truncated, meaning the tail of every chunk was never embedded and could never be retrieved. Reducing to 400 tokens gives comfortable headroom under that limit. The 80-token overlap (20% ratio, matching the original spec's proportion) ensures that a sentence split across a chunk boundary still appears in at least one complete chunk. Before chunking, documents were cleaned to remove RTF formatting artifacts (the source files were saved from my Mac TextEdit in RTF format), Reddit flair labels ("Discussion", "Question"), standalone URLs, HTML entities, and zero-width Unicode characters.

**Final chunk count:** 55 chunks across 10 documents

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2 via sentence-transformers library

**Production tradeoff reflection:**
For a real deployment, I would consider text-embedding-3-large (OpenAI) or BGE-M3 (BAAI). The key tradeoffs are: (1) context length — all-MiniLM-L6-v2's 512-token limit forced smaller chunks, whereas models like BGE-M3 support up to 8,192 tokens, allowing richer per-chunk context; (2) domain accuracy — a model fine-tuned on informal social media text would likely outperform a general-purpose model on Reddit content; (3) latency — local models like all-MiniLM are fast at query time, while API-hosted models add network latency but remove the need to manage local GPU/CPU resources; (4) multilingual support — not relevant here but critical if the student population is international.


---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
You are a helpful assistant for Penn State University students looking for
information about off-campus housing, landlords, parking, and commuting
in State College, PA.

RULES YOU MUST FOLLOW:
1. Answer ONLY using information from the provided sources below.
2. Do NOT use your general training knowledge about housing, landlords,
   or State College.
3. If the sources don't contain enough information to answer the question,
   say exactly: "I don't have enough information on that in my sources."
4. Cite your sources inline using [Source N] notation when you use
   information from them.
5. Be specific - quote apartment names, specific advice, or exact details
   when they appear in the sources.
6. Keep your answer focused and under 200 words.

**How source attribution is surfaced in the response:**
The model cites sources inline using [Source N] notation when it uses information from the provided documents.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What strategies do Penn State students recommend for commuting in harsh winter weather? | Use public transportation, layer clothing, use CATA buses | Thermal layers, Gore-Tex boots, hand warmers, neck gaiters, balaclava, walk through buildings, all with inline source citations | Relevant | Accurate |
| 2 | Which specific apartment complexes do students warn others to avoid in State College? | Tremont, The Bryn, The Pointe. | Correctly named all three complexes and cited the PSA thread, but Borough Council chunks appeared at ranks 1–4 due to volume dominance | Partially relevant | Accurate |
| 3 | What do students say causes traffic backups and CATA bus delays near campus? | Long commutes, traffic, underfunding | Boarding/unboarding time not in timetables, students not moving to the back, parents parking at bus stops, state funding cuts | Relevant | Accurate |
| 4 | What are the most common misconceptions about parking permits at Penn State? | Limited and expensive parking | Having class is not a valid exception; open spots on a counter don't mean a garage is open; each pass is only valid for specific lots | Relevant | Accurate |
| 5 | What specific maintenance or management issues do students report about State College landlords?| Mixed reviews, maintenance and management issues | Unexpected rent increases, removal of included utilities, uncleaned apartments between tenants, Parkway Plaza named specifically| Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
"Which specific apartment complexes do students warn others to avoid in State College?"

**What the system returned:**
The correct answer (Tremont, The Bryn, The Pointe) appeared in the response, but the PSA thread only appeared at rank 5 in retrieval. Ranks 1–4 were all from the Borough Council zoning thread. The LLM still cited [Source 5] correctly for the apartment names, but the sources footer listed Borough Council as a retrieved source, which is misleading.

**Root cause (tied to a specific pipeline stage):**
The failure was most likely in Stage 3 (Embedding) and Stage 4 (Retrieval). The Borough Council thread is the longest document in the corpus, it was split into 11 chunks, while the Tremont PSA has only 5 chunks. Because cosine similarity is computed independently per chunk, a document with more chunks has more chances to appear in the top-5. The Borough Council thread uses the words "State College," "students," and "housing" heavily throughout, giving it high semantic overlap with any housing-related query even when it contains no information about specific apartment complexes. This is a chunk volume dominance problem: a large, topically broad document crowds out a smaller, more specific document.

**What you would change to fix it:**
Two fixes I could think of: (1) In retrieve.py, cap results at 2 chunks per source title (a diversity guard), so no single document can fill all 5 retrieval slots. (2) During chunking, consider splitting the Borough Council thread into topically coherent sections (zoning policy, housing supply, commuting) rather than purely by token count, so each chunk is more semantically focused and less likely to match unrelated queries.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
The planning.md spec required writing down the chunk size and overlap before writing any code. This forced an early decision (1,000 tokens, 200 overlap) that turned out to be wrong, but having it written down made it easy to diagnose when the embedding model started silently truncating chunks. Without the explicit number in the spec, the bug would have been much harder to catch: the system would have appeared to work while the tail of every chunk went unembedded. The spec essentially created a checkable contract against the actual behavior.

**One way your implementation diverged from the spec, and why:**
The spec called for 1,000-token chunks with 200-token overlap. The final implementation uses 400-token chunks with 80-token overlap. The reason was a hard constraint in the embedding model that the spec did not account for: all-MiniLM-L6-v2 silently truncates any input over 512 tokens. This means a 1,000-token chunk would have its second half completely ignored during embedding — the vector would represent only the first 512 tokens, and any information in the remaining 488 tokens could never be retrieved. Reducing chunk size to 400 tokens ensures every chunk is fully embedded, and scaling the overlap proportionally (80/400 = 20%, matching the original 200/1000 = 20% ratio) preserved the original design intent.
---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
I gave the AI my Chunking Strategy section from planning.md and asked it to implement chunk_text(). It returned a function using a fixed character split.
- *What it produced:*
A working chunk_text() function using a sliding window over tiktoken tokens, a doc_to_segments() function that separates post bodies from comment threads before chunking, and metadata attachment for each chunk (source_id, source_url, segment_type, chunk_index).
- *What I changed or overrode:*
The initial output used a word-based token approximation (words / 0.75) rather than tiktoken. I identified this from the output showing 1,333 stored tokens on chunks that should have been 1,000, the approximation overcounts. I directed Claude to fix the fallback logic and confirm tiktoken was the primary path. I also reduced chunk size from 1,000 to 400 tokens after discovering the all-MiniLM-L6-v2 512-token limit.

**Instance 2**

- *What I gave the AI:*
The 10 Reddit source files in RTF format (accidentally saved from Mac TextEdit), plus the ingest.py script that expected plain .txt input. Asked Claude to diagnose why the ingestion was producing garbled output.
- *What it produced:*
RTF files contain formatting codes (like \par, \b, \i) that plain text parsers treat as content, causing token counts to inflate and chunks to break mid-sentence. Suggested using python-docx for RTF parsing or converting to plain text first.
- *What I changed or overrode:*
I converted the RTF files to plain text using a simple script that stripped the formatting codes, then re-ran the ingestion. This resolved the garbled output and produced clean, tokenized chunks.
