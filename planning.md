# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
I chose the domain of "Lease or Lose: Off-Campus Housing Guide". This knowledge is valuable because it provides students with information about off-campus housing options, lease terms, and other important details that they need to know before signing a lease. It is hard to find through official channels because it is not always readily available on official websites or through official channels. I also focus on commuting and parking issues that students face when living off-campus. I used Reddit threads as my source of information, because students post regularly their reviews and experiences with different housing options. I am from State College, so I chose to focus on off-campus housing options in State College.
---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | Reddit | PSA: For Students Looking for Off-Campus Housing in STATE COLLEGE: AVOID TREMONT, THE BRYN & THE POINTE | https://www.reddit.com/r/PennStateUniversity/comments/smf10g/psa_for_students_looking_for_offcampus_housing_in/?utm_source=embedv2&utm_medium=post_embed&utm_content=whitespace&embed_host_url=https%3A%2F%2Fembed.notion.co%2Fapi%2Fiframe |
| 2 | Reddit | The landlord issue in State College should be studied | https://www.reddit.com/r/PennStateUniversity/comments/1ni0lot/the_landlord_issue_in_state_college_should_be/ |
| 3 | Reddit | what's up with traffic/CATA this sem? | https://www.reddit.com/r/PennStateUniversity/comments/1n6ls91/whats_up_with_trafficcata_this_sem/ |
| 4 | Reddit | Just a quick question, how tf do people walk anywhere in this bitterly cold weather? | https://www.reddit.com/r/PennStateUniversity/comments/1qzfs2p/just_a_quick_question_how_tf_do_people_walk/ |
| 5 | Reddit | Hi everyone, I work in parking for PSU. Please read this to better understand parking on campus | https://www.reddit.com/r/PennStateUniversity/comments/1mjjbkn/hi_everyone_i_work_in_parking_for_psu_please_read/|
| 6 | Reddit | Hi everyone, I work in parking for PSU. Please read this to better understand parking on campus | https://www.reddit.com/r/PennStateUniversity/comments/1mjjbkn/hi_everyone_i_work_in_parking_for_psu_please_read/ |
| 7 | Reddit | Fall Only Housing | https://www.reddit.com/r/PennStateUniversity/comments/16jgrcu/fall_only_housing/ |
| 8 | Reddit | Reminder to Rate your Landlords and Professors | https://www.reddit.com/r/PennStateUniversity/comments/1te4l4y/reminder_to_rate_your_landlords_and_professors/ |
| 9 | Reddit | Desperate for Sublease | https://www.reddit.com/r/PennStateUniversity/comments/1ov8oim/desperate_for_sublease/ |
| 10 | Reddit | Moving up from the midwest, The landlords in State College are leeches | https://www.reddit.com/r/PennStateUniversity/comments/ou3v1i/moving_up_from_the_midwest_the_landlords_in_state/ |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**
The average Reddit post is around 500-1000 words, so I'll use a chunk size of 1000 tokens with 200 token overlap to ensure context is maintained.

**Overlap:**
200 tokens

**Reasoning:**
This ensures that important context is not lost when chunks are created, while still maintaining a reasonable chunk size for processing.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
all-MiniLM-L6-v2

**Top-k:**
5

**Production tradeoff reflection:**
If I were deploying this for real users and cost wasn't a constraint, I would consider using a more advanced embedding model like BGE-M3 or Multilingual-E5-Large-Instruct to improve accuracy on domain-specific text. However, all-MiniLM-L6-v2 provides a good balance between accuracy and speed for this use case.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 |  How do penn state students survive commuting in harsh weather? | Use public transportation or carpooling | 
| 2 | What are some tips for finding off-campus housing in State College? | Avoid Tremont, The Bryn, and The Pointe |
| 3 | What are some common complaints about commuting to Penn State University? | Long commutes and traffic |  
| 4 | What do students say about parking at Penn State University? | Limited and expensive | 
| 5 | What do students say about the quality of off-campus housing in State College? | Mixed reviews, with some students reporting issues with maintenance and management |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Noisy or inconsistent documents - Some documents may have inconsistent formatting or contain irrelevant information that could affect the accuracy of the system.

2. Missing source attribution - Some documents may not have proper source attribution, which could lead to incorrect information being provided to users.

---

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

     **Milestone 2 — Document ingestion:**
     - AI Tool: Claude
     - Input: Document Ingestion section of this planning.md
     - Expected Output: Function to read and parse documents
     - Verification: Check if function correctly reads and parses documents

**Milestone 3 — Ingestion and chunking:**
     - AI Tool: Claude
     - Input: Chunking Strategy section of this planning.md
     - Expected Output: Function to chunk documents
     - Verification: Check if function correctly chunks documents

**Milestone 4 — Embedding and retrieval:**
     - AI Tool: Claude
     - Input: Embedding Strategy section of this planning.md
     - Expected Output: Function to embed and retrieve documents
     - Verification: Check if function correctly embeds and retrieves documents

**Milestone 5 — Generation and interface:**
     - AI Tool: Claude
     - Input: Generation Strategy section of this planning.md
     - Expected Output: Function to generate responses
     - Verification: Check if function correctly generates responses
