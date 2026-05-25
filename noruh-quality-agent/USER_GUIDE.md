# User Guide
## Noruh Manufacturing Quality Agent — v2.0

**For:** Quality engineers at Noruh Manufacturing  
**Assumes:** Setup is already complete (Python installed, Ollama running, models downloaded, database generated)

---

## Table of Contents

1. [What the App Does](#1-what-the-app-does)
2. [Starting the App](#2-starting-the-app)
3. [Reading the Sidebar Status](#3-reading-the-sidebar-status)
4. [Asking a Question](#4-asking-a-question)
5. [Understanding the Ishikawa Output](#5-understanding-the-ishikawa-output)
6. [The Streaming Panel — What You See While It Thinks](#6-the-streaming-panel--what-you-see-while-it-thinks)
7. [The Raw Output Expander](#7-the-raw-output-expander)
8. [Troubleshooting](#8-troubleshooting)
9. [Limitations](#9-limitations)
10. [Example Walkthrough](#10-example-walkthrough)
11. [Quick Reference Card](#11-quick-reference-card)

---

## 1. What the App Does

The Noruh Manufacturing Quality Agent is a private AI assistant that runs entirely on your laptop. You type a question about a quality problem — a complaint spike, a dimensional failure, a packaging defect — and the app searches five years of factory data to find the most likely root causes. It then presents its findings in an Ishikawa (fishbone) framework: the same structure you already use in quality reviews, now generated automatically in minutes instead of hours.

Nothing leaves your machine. The AI models run locally, the factory data stays local, and no query or result is ever sent to the internet. Once the setup is done, the app works with no network connection at all.

The database covers five years of production history for the Top, Leg, and Stand components — about 1.5 million rows across CNC telemetry, lab dimensional tests, packaging line records, and customer warranty claims.

---

## 2. Starting the App

**On Windows:** Double-click `start_windows.bat` in the project folder. A terminal window will open briefly and then your browser will navigate automatically to the app. If the browser does not open on its own, type `http://localhost:8501` into the address bar.

**On macOS or Linux:** Open a terminal in the project folder and run:

```
streamlit run app.py
```

The app typically takes 5–10 seconds to start. Once the browser shows the dashboard, you are ready.

> If you see a spinning indicator for more than 30 seconds, check the Troubleshooting section.

---

## 3. Reading the Sidebar Status

The left sidebar shows three status chips. Think of them as a preflight checklist — all three should be green before you ask a question.

**Database** — Confirms that the DuckDB factory history file is open and readable. This is almost always green unless the database file was moved or deleted.

**Ollama** — Confirms that the local AI model server is running. If this shows orange or "Offline", the app cannot run an analysis. See the Troubleshooting section.

**Vector store** — Confirms that the customer complaint search index is loaded. If this shows orange, the app will still work but complaint-text similarity search will fall back to a simpler keyword method.

Green means the component is healthy and ready. Orange means the component is degraded but the app may still partially function. A red or "Offline" label means the component is unavailable and analysis will fail or be incomplete.

---

## 4. Asking a Question

The chat input bar sits at the bottom of the main panel. Type your question there in plain language and press Enter.

You do not need to use special syntax or keywords. Write the question the way you would ask a colleague: *"Why did fitment complaints spike in Q2 2022?"* or *"What caused the gouge defects in October 2024?"* The agent understands manufacturing terminology and will translate your question into the right database queries automatically.

**Example questions** are listed above the input bar. Click any of them to copy it into the input field — useful as a starting point or as a way to see what kinds of questions the agent handles well.

The five built-in examples are:

1. *"Why did fitment complaints spike in Q2 2022?"*
2. *"Investigate the surface finish issues from summer 2023."*
3. *"What caused the gouge defects in October 2024?"*
4. *"Analyse the missing hardware claims from November 2025."*
5. *"Give me a full quality overview for Year 3 across all machines."*

After you submit a question, the agent begins working. A targeted question (one specific event, one time period) typically takes **1–3 minutes**. A broad question covering a whole year or multiple machines may take up to **6 minutes**. This is normal — the AI models run on the CPU and take time to reason through the evidence.

---

## 5. Understanding the Ishikawa Output

When the analysis is complete, the answer appears as a grid of coloured cards, one for each of the four Ishikawa cause categories. If you have used fishbone diagrams in quality reviews, the categories will be familiar — but here they are generated from real data rather than brainstormed by a team.

**Machine** — Root causes tied to CNC equipment, tooling, calibration, or sensor readings. A typical finding here might be a specific machine showing dimensional drift, or vibration exceeding safe limits. These causes point to maintenance, calibration checks, or equipment replacement.

**Material** — Root causes tied to raw material quality, tooling consumables, or incoming stock. A finding here might note that surface roughness spiked when a lower-grade cutting tool batch was introduced. These causes point to supplier management or procurement standards.

**Method** — Root causes tied to processes, procedures, or settings. A finding here might identify a change in feed rate, cutting speed, or inspection protocol that preceded a defect wave. These causes point to process control, work instructions, or SPC limits.

**Human / Environment** — Root causes tied to operator behaviour, training, shift patterns, or ambient factory conditions. A finding here might identify a specific operator associated with a defect type, or a shift pattern linked to a higher scrap rate. These causes point to training, supervision, or ergonomic review.

Each card contains a list of specific, data-backed findings. Below the cards, a **summary** paragraph gives an executive narrative: a plain-language account of what the data shows and which anomaly or combination of causes best explains the problem.

The `anomalies_found` field, if populated, will list the anomaly IDs (such as ANOM-01) that the agent identified. These IDs correspond to the known data events described in the system documentation.

---

## 6. The Streaming Panel — What You See While It Thinks

While the agent is working, the streaming panel shows you its reasoning steps in real time. You do not need to wait in the dark.

**SQL statements** — As the agent generates database queries, each one appears with a small preview of how many rows it returned. This tells you which tables and time periods the agent searched. For example, you might see a query filtering `cnc_telemetry` by machine and date range, followed by `(42 rows)`.

**Critic review expanders** — After the first pass of evidence gathering, the agent's reasoning model reviews the findings and decides whether it has enough information. If it decides more data is needed (marked `INSUFFICIENT`), you will see a summary of what it found lacking and the agent will run another round of queries. This self-correction loop runs up to three times. You will see each round appear as a new expander in the streaming panel.

**SUFFICIENT** — When the critic is satisfied with the evidence, you will see this label, and the agent moves on to formatting the final answer.

If the streaming panel shows activity for more than 6–7 minutes without completing, refer to the Troubleshooting section.

---

## 7. The Raw Output Expander

At the bottom of every completed answer there is a collapsible section labelled **"Raw model output"**. Clicking it reveals the unformatted JSON that the AI model produced before it was parsed into the card display.

Most of the time you will not need this. It is provided for cases where you want to verify a specific data point in the answer, compare what the model said against the structured cards, or report an unexpected result. If you are contacting technical support about a wrong or incomplete answer, including the raw output helps with diagnosis.

---

## 8. Troubleshooting

### Ollama shows "Offline"

The local AI model server is not running. To fix this:

1. Open a terminal (or Command Prompt on Windows).
2. Type `ollama serve` and press Enter.
3. Wait 10–15 seconds, then refresh the browser. The sidebar chip should turn green.

If `ollama serve` produces an error saying the server is already running, try closing and reopening the browser tab rather than restarting Ollama.

### The answer seems wrong or incomplete

The agent can only work with the data in its database. If a quality event is not captured in the five years of factory history (for example, a very recent event that occurred after the database snapshot), the agent will not find evidence for it.

If the agent returns a response that says it could not find sufficient evidence, try rephrasing the question with a more specific time range or component type. For example, instead of *"Are there any quality problems?"*, try *"What quality issues affected the Leg component in Q3 2023?"*

If the answer appears to be missing a cause you expected, check whether the question covered the relevant time period. The agent searches only the date ranges implied by your question.

### The app is very slow

Normal analysis times are 1–3 minutes for targeted questions and up to 6 minutes for broad ones. If a response takes longer than 8 minutes, the AI model may have stalled. Close the browser tab, stop the Streamlit process (press Ctrl+C in the terminal), and restart with `start_windows.bat` or `streamlit run app.py`.

Slow performance can also occur if other applications are consuming large amounts of RAM. The agent needs up to 12 GB of RAM for inference. Closing other memory-heavy applications (browsers with many tabs, video editing software) before running an analysis will help.

### The browser shows a Streamlit connection error

The Streamlit server has stopped. Restart the app using `start_windows.bat` or `streamlit run app.py` in the terminal.

---

## 9. Limitations

Understanding what the agent cannot do is as important as knowing what it can.

**The agent only knows the five years of history in the database.** It has no connection to live production systems, real-time machine sensors, or current ERP/MES data. If you ask about an event from last week that is not yet in the database, it will find no evidence.

**The agent cannot take corrective action.** It reads and analyses; it does not write to any system, raise maintenance work orders, flag parts for hold, or send notifications. All decisions and follow-up actions remain with you.

**The agent cannot connect to external systems.** There is no integration with your plant's PLC network, ERP, quality management system, or any external database. The analysis is entirely self-contained within the local dataset.

**Conversation history does not persist between sessions.** If you close the browser or restart the app, the conversation history shown on screen is cleared. The factory database itself is not affected.

**The agent can be wrong.** Like any analytical tool, it can miss causes, draw incorrect inferences from ambiguous data, or fail to identify a cause that is not well-represented in the database. Treat its output as a starting point for investigation, not a final verdict. Use your own engineering judgement to verify findings before acting on them.

---

## 10. Example Walkthrough

### Question: "Why did fitment complaints spike in Q2 2022?"

This is one of the five example questions and corresponds to a real pattern in the database. Here is what a good answer looks like and how to interpret it.

**What the agent does first:** It queries `customer_feedback` for complaints in the April–June 2022 window, filtering for fitment-related keywords. It also queries `cnc_telemetry` for the same period, looking for dimensional deviation trends, and `lab_testing` for CMM out-of-spec records.

**What the streaming panel shows:** You will see two or three SQL queries appear, each with a row-count preview. After the first pass, the critic will typically find enough dimensional evidence to proceed and return `SUFFICIENT` without a retry loop.

**What the Ishikawa cards show:**

- **Machine:** Machine B dimensional deviation increasing from 0.01 mm to 0.25 mm over the April–June 2022 period — a classic calibration drift signature. This is ANOM-01.
- **Material:** Possibly no significant finding, or a note that tooling was within normal spec during this period.
- **Method:** No procedural change identified in the period.
- **Human / Environment:** No operator-specific pattern linked to the complaint spike.

**The summary paragraph** will state that the complaint spike is explained by Machine B calibration drift causing dimensional deviations that exceeded fitment tolerance, with the drift progressing over the quarter before being corrected. The `anomalies_found` field will list `ANOM-01`.

**How to use this result:** The finding points directly to Machine B's calibration history. The corrective action path would be to review Machine B's calibration records for Q2 2022, confirm when recalibration occurred, assess whether the affected parts were shipped to customers, and review the calibration interval to prevent recurrence.

---

## 11. Quick Reference Card

### How to Start

| Platform | Action |
|----------|--------|
| Windows | Double-click `start_windows.bat` |
| macOS / Linux | Run `streamlit run app.py` in terminal |
| Browser address | `http://localhost:8501` |

---

### Five Example Questions

1. *"Why did fitment complaints spike in Q2 2022?"*
2. *"Investigate the surface finish issues from summer 2023."*
3. *"What caused the gouge defects in October 2024?"*
4. *"Analyse the missing hardware claims from November 2025."*
5. *"Give me a full quality overview for Year 3 across all machines."*

---

### Sidebar Status Chips

| Colour | Meaning |
|--------|---------|
| Green | Component ready — proceed normally |
| Orange | Component degraded — analysis may be incomplete |
| Offline / Red | Component unavailable — analysis will fail |

---

### Ishikawa Card Categories

| Card | What it covers |
|------|----------------|
| Machine | CNC equipment, calibration, sensors |
| Material | Tooling, raw material, consumables |
| Method | Process settings, procedures, SPC limits |
| Human / Environment | Operator behaviour, training, shift patterns |

---

### Typical Response Times

| Question type | Expected time |
|---------------|---------------|
| Targeted (one event, one period) | 1–3 minutes |
| Broad (full year, multiple machines) | 3–6 minutes |

---

### What to Do If…

| Problem | Action |
|---------|--------|
| Ollama chip shows "Offline" | Open terminal → run `ollama serve` → refresh browser |
| Answer seems incomplete | Rephrase with a specific date range or component name |
| No response after 8 minutes | Ctrl+C to stop → restart the app |
| Browser shows connection error | Restart the app |
| Need to report a wrong answer | Open "Raw model output" expander and include it in your report |
