# Handoff Prompt — Requirements Doc & User Guide Session

Paste this entire block as the opening message in the new chat.
Attach the file `noruh_architecture.png` from the same folder alongside it.

---

## Context

You are writing two documents for a completed software project:
**Noruh Manufacturing Quality Agent** — a fully local, offline AI analytics
dashboard that diagnoses manufacturing root causes for a company that produces
premium modular stainless steel end tables (three components: Top, Leg, Stand).

The software is **already built and working**. Your job is to document it, not
change it. Do not suggest code changes.

---

## What the software does

A Streamlit web dashboard runs entirely on a user's laptop (no internet needed
after setup). The user types a natural-language question about manufacturing
quality — for example: *"Why did fitment complaints spike in Q2 2022?"* — and
the agent:

1. Generates SQL queries against a local DuckDB database (5 years of factory
   history: ~1.5 million rows across CNC telemetry, lab testing, packaging
   logs, and customer feedback)
2. Searches a vector database of customer complaints using semantic similarity
3. Runs those queries against real data
4. Has a second AI model critique the findings and request more data if needed
   (up to 3 self-correction passes)
5. Returns a structured **Ishikawa fishbone root-cause analysis** with four
   categories: Machine · Material · Method · Human/Environment
6. Displays the answer as colour-coded cards in the browser

The architecture diagram is attached as `noruh_architecture.png`.

### AI models used (run via Ollama, locally on the laptop)
| Role | Model | Purpose |
|------|-------|---------|
| Tool-Calling Engine | qwen3-coder:7b (~4.7 GB) | Writes SQL, performs semantic search |
| Refining Thinking Engine | deepseek-r1:8b (~4.9 GB) | Critiques results, decides if more data is needed |

Both models run sequentially (one at a time) to keep peak RAM within 12 GB.

### Database contents (synthetic — 5 years of factory history)
| Table | Rows | Description |
|-------|------|-------------|
| cnc_telemetry | 657,360 | Per-part CNC machine sensor readings |
| lab_testing | 656,083 | CMM dimensional and surface finish test results |
| packaging_log | 218,230 | Packaging line pass/fail records |
| customer_feedback | 10,838 | Warranty claims and complaint texts |

### Five known anomalies in the data (agent must find these)
| ID | Period | Description |
|----|--------|-------------|
| ANOM-01 | Apr–Jun 2022 | Machine B calibration drift — dimensional deviation ramps 0.01→0.25 mm |
| ANOM-02 | Jun–Aug 2023 | Cheap tooling campaign — surface roughness (Ra) 2.4× baseline |
| ANOM-03 | Oct 2024 | New operator OP-007 gouge events — 76 FAIL_GOUGE parts at 6% rate |
| ANOM-04 | Ongoing | Tool-breakage inline scrap — 1,277 rejections (vibration > 3.5 g) |
| ANOM-05 | Nov 1–14 2025 | PKG-003 packaging station missing hardware — 64 claims at 8% rate |

### Five example questions in the UI
1. "Why did fitment complaints spike in Q2 2022?"
2. "Investigate the surface finish issues from summer 2023."
3. "What caused the gouge defects in October 2024?"
4. "Analyse the missing hardware claims from November 2025."
5. "Give me a full quality overview for Year 3 across all machines."

---

## Technical stack (for the requirements doc)
- **UI**: Streamlit (Python web framework, runs in browser)
- **Agent framework**: LangGraph (state machine with 4 nodes)
- **Local LLM runtime**: Ollama (serves models via localhost:11434)
- **Structured database**: DuckDB (embedded SQL, read-only)
- **Vector database**: ChromaDB with BAAI/bge-small-en-v1.5 embeddings
  (falls back to TF-IDF offline)
- **SQL safety**: sqlglot AST + regex injection guard (blocks all write operations)
- **Output schema**: Pydantic v2 `IshikawaAnalysis` model

### Hardware requirements (minimum)
- 16 GB RAM (12 GB needed at peak inference)
- 20 GB free disk space
- Windows 10/11 or macOS or Linux
- No GPU required — runs on CPU only
- No internet connection required after initial setup

### Setup time (one-time)
- Python + packages: ~15 minutes
- Ollama model downloads (~8.4 GB total): 30–90 minutes depending on internet
- Database generation: ~80 seconds (automated)

---

## What to produce

### Document 1: Product Requirements Document (PRD)

Audience: technical reviewers, future developers, project sponsors.

Must cover:
- Project overview and business problem
- Goals and success criteria
- User personas and use cases
- Functional requirements (what the system does)
- Non-functional requirements (performance, security, offline operation,
  RAM constraints, response time targets)
- Data requirements (the 5 tables, the 5 anomalies, data generation)
- AI/LLM requirements (models, sequential loading, retry logic, output schema)
- Security requirements (SQL injection prevention, read-only access,
  no data leaving the machine)
- Deployment requirements (Windows, macOS, Linux; CPU-only; offline)
- Out of scope (what the system deliberately does not do)
- Glossary

Format: clean Markdown, suitable for a GitHub README or internal wiki.

---

### Document 2: User Guide

Audience: a manufacturing quality engineer who is NOT a developer. They
understand quality engineering concepts (Ishikawa, FMEA, SPC) but do not
know Python, AI models, or command-line tools.

The user has already completed setup (Python installed, Ollama installed,
models downloaded, database generated). This guide covers **using the app
day-to-day**, not setting it up.

Must cover:
- What the app does in plain language (no jargon)
- How to start the app (double-click start_windows.bat on Windows)
- Understanding the sidebar: Database / Ollama / Vector store status chips
- Understanding the health indicators (green = ready, orange = warning)
- How to ask a question (chat input at the bottom, or click an example question)
- How to read the Ishikawa output cards (Machine / Material / Method /
  Human·Environment — what each category means in a manufacturing context)
- How to read the "Raw model output" expander (for debugging)
- Interpreting the streaming panel: live SQL, row count previews, critic
  review expanders
- What to do if Ollama shows "offline"
- What to do if the answer seems wrong or incomplete
- Limitations: the agent only knows the 5-year history in the database;
  it cannot connect to live production systems; it cannot take corrective
  action
- Example walkthrough: paste one full sample question and annotate what a
  good answer looks like, referencing the five anomalies

Format: clean Markdown with clear section headers. Write as if explaining to
a smart, senior engineer who has never seen the app. No bullet-point soup —
use short prose paragraphs where possible. Include a Quick Reference card
at the end (one-page cheat sheet: how to start, 5 example questions,
status chip meaning, what to do if X).

---

## Files to create

Save both documents in the `noruh-quality-agent/` folder:

- `REQUIREMENTS.md` — the PRD
- `USER_GUIDE.md` — the user guide

Commit both to the branch `claude/zen-rubin-iwVgV` in the repo
`lrsolano847-ux/LeanSigma-AI` and push when done.

---

## Important constraints

- Do not invent features that don't exist. Everything described above is real
  and implemented.
- Do not suggest code changes or improvements to the software.
- The company name is **Noruh Manufacturing**. The product line is premium
  modular stainless steel end tables with three components: Top, Leg, Stand.
- The agent is described internally as a **local, offline, CPU-only** system.
  This is a key selling point — emphasise it appropriately.
- All inference is private: no data leaves the machine.
- The Ishikawa framework (fishbone diagram) is the primary output structure.
  The user guide should briefly explain what Ishikawa is for readers who know
  the concept but may not have seen it in a software context before.
