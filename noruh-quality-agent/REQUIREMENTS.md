# Product Requirements Document
## Noruh Manufacturing Quality Agent — v2.0

**Document status:** Final  
**Date:** May 2026  
**Audience:** Technical reviewers, future developers, project sponsors

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Business Problem](#2-business-problem)
3. [Goals and Success Criteria](#3-goals-and-success-criteria)
4. [User Personas and Use Cases](#4-user-personas-and-use-cases)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Data Requirements](#7-data-requirements)
8. [AI / LLM Requirements](#8-ai--llm-requirements)
9. [Security Requirements](#9-security-requirements)
10. [Deployment Requirements](#10-deployment-requirements)
11. [Out of Scope](#11-out-of-scope)
12. [Glossary](#12-glossary)

---

## 1. Project Overview

The **Noruh Manufacturing Quality Agent** is a fully local, offline, CPU-only AI analytics dashboard that assists manufacturing quality engineers in diagnosing the root causes of defects, complaints, and process failures. It runs as a Streamlit web application entirely on the user's laptop — no internet connection, no cloud services, and no external data transmission are involved during normal operation.

The agent accepts natural-language questions about manufacturing quality events and returns structured Ishikawa fishbone root-cause analyses drawn from five years of synthetic factory history for **Noruh Manufacturing**, a producer of premium modular stainless steel end tables (three components: Top, Leg, Stand).

The system was developed to validate a reference architecture for private, on-premises AI-assisted quality management. It uses two local large language models (LLMs) served by Ollama, a LangGraph multi-agent state machine, a DuckDB structured database, and a ChromaDB vector store.

---

## 2. Business Problem

Manufacturing quality investigations are time-consuming. A quality engineer confronted with a spike in customer complaints, a CMM failure trend, or an unexplained scrap rate must manually query multiple data systems, correlate timestamps across telemetry logs, lab results, and complaint records, and then synthesise findings into a structured root-cause narrative.

This process typically takes hours to days. Small-to-medium manufacturers often lack dedicated data-science resources, so the analysis either is not performed or is performed superficially.

The agent reduces the time-to-insight from hours to minutes by automating query generation, data retrieval, evidence critique, and structured reporting — all without exposing proprietary factory data to any external service.

---

## 3. Goals and Success Criteria

### Goals

- Allow a quality engineer to ask a natural-language question and receive a structured, evidence-backed Ishikawa root-cause analysis within a single session.
- Operate entirely on a factory-floor laptop with no internet connection after initial setup.
- Keep peak RAM consumption below 12 GB so the system can coexist with other applications on a 16 GB machine.
- Detect all five injected data anomalies (ANOM-01 through ANOM-05) when the corresponding questions are asked.
- Provide a streaming UI that gives the engineer live visibility into the agent's reasoning steps.

### Success Criteria

| Criterion | Target |
|-----------|--------|
| Response time for a targeted question | ≤ 3 minutes on reference hardware |
| Response time for a broad overview question | ≤ 6 minutes on reference hardware |
| Peak RAM during inference | ≤ 12 GB |
| Anomaly detection rate | 5 / 5 known anomalies detectable |
| SQL injection attempts blocked | 100% (all write operations rejected) |
| Data leaving the machine | 0 bytes |
| Offline operation (after setup) | Full functionality |

---

## 4. User Personas and Use Cases

### Primary Persona — Quality Engineer

**Name:** Senior Quality Engineer at Noruh Manufacturing  
**Background:** Deep knowledge of quality engineering methodologies (Ishikawa, FMEA, SPC, CMM interpretation). No background in Python, AI models, or database administration.  
**Goal:** Quickly diagnose the root cause of a quality event — a complaint spike, a dimensional failure trend, a packaging defect — without involving IT or data science.  
**Constraint:** Works on a standard factory-floor laptop; cannot install cloud software or send data externally.

### Secondary Persona — Technical Reviewer / Developer

**Background:** Software engineer or data scientist evaluating the architecture as a reference implementation.  
**Goal:** Understand the system design, data pipeline, and AI orchestration well enough to extend or adapt it.

### Use Cases

| ID | Use Case | Trigger |
|----|----------|---------|
| UC-01 | Investigate a complaint spike by time period | Customer service escalation |
| UC-02 | Diagnose a surface finish failure trend | Lab CMM report out-of-spec |
| UC-03 | Identify root cause of gouge defects | Operator shift report |
| UC-04 | Analyse missing-hardware packaging claims | Warranty return increase |
| UC-05 | Generate a broad quality overview for a year | Monthly quality review meeting |

---

## 5. Functional Requirements

### 5.1 User Interface

**FR-UI-01** The system shall provide a Streamlit web dashboard accessible in the user's browser at `http://localhost:8501`.

**FR-UI-02** The sidebar shall display status chips indicating the live connection state of the DuckDB database, the Ollama LLM server, and the ChromaDB vector store. Each chip shall show a colour-coded health indicator (green = ready, orange = degraded/warning).

**FR-UI-03** The main input area shall include a text input field for natural-language questions.

**FR-UI-04** The UI shall display five example questions that the user can click to populate the input field.

**FR-UI-05** A streaming panel shall display live agent progress, including generated SQL statements, row-count previews of query results, and critic-review summaries, while the agent is processing.

**FR-UI-06** The final answer shall be rendered as a grid of colour-coded Ishikawa category cards: Machine, Material, Method, and Human/Environment.

**FR-UI-07** A collapsible "Raw model output" expander shall make the unformatted model JSON available for debugging.

**FR-UI-08** The UI shall maintain a conversation history panel showing prior questions and their answers within the session.

### 5.2 Agent Engine

**FR-AG-01** The agent shall be implemented as a LangGraph state machine with four sequential nodes: `tool_caller`, `tool_executor`, `critic`, and `ishikawa_formatter`.

**FR-AG-02** The `tool_caller` node shall use the `qwen3-coder:7b` model to interpret the user's question, generate one or more SQL queries against the DuckDB schema, and optionally invoke a semantic search against the vector store. Output shall be structured as tool calls in JSON.

**FR-AG-03** The `tool_executor` node shall execute the tools generated in FR-AG-02 and return results to the agent state.

**FR-AG-04** The `critic` node shall use the `deepseek-r1:8b` model to evaluate the gathered evidence and render a verdict of `SUFFICIENT` or `INSUFFICIENT`. If `INSUFFICIENT`, the node shall emit a refined query request and the graph shall loop back to `tool_caller`. The maximum number of retry passes is **3**.

**FR-AG-05** The `ishikawa_formatter` node shall parse the final model output into a validated `IshikawaAnalysis` Pydantic v2 model and return it to the UI.

**FR-AG-06** The agent shall stream events to the UI throughout processing so that the user receives live feedback rather than waiting for a complete response.

### 5.3 Tools

**FR-TL-01** `execute_sql(sql)` — Executes a read-only SQL query against the DuckDB database and returns rows as a JSON-serialisable result. Any query containing write operations shall be rejected before execution.

**FR-TL-02** `semantic_search(query, n)` — Searches the ChromaDB vector store using cosine similarity against BAAI/bge-small-en-v1.5 embeddings and returns the top-`n` matching customer feedback documents. If the vector store is unavailable, the tool shall fall back to TF-IDF-based search.

### 5.4 Output Schema

**FR-OUT-01** The final output shall conform to the `IshikawaAnalysis` Pydantic v2 schema:

| Field | Type | Description |
|-------|------|-------------|
| `machine` | `list[str]` | CNC / equipment root causes |
| `material` | `list[str]` | Tooling / material root causes |
| `method` | `list[str]` | Process / procedure root causes |
| `human_environment` | `list[str]` | Operator / ambient / factory root causes |
| `summary` | `str` | Executive narrative |
| `anomalies_found` | `list[str]` | Anomaly IDs identified (e.g., ANOM-01) |

---

## 6. Non-Functional Requirements

### 6.1 Performance

**NFR-P-01** Targeted single-anomaly questions shall return a complete answer in ≤ 3 minutes on the reference hardware specification.

**NFR-P-02** Broad overview questions (e.g., full-year analysis across all machines) shall return a complete answer in ≤ 6 minutes on reference hardware.

**NFR-P-03** Peak RAM consumption during inference shall not exceed 12 GB. The two AI models shall be loaded sequentially (one at a time) and evicted from RAM between calls.

**NFR-P-04** The Streamlit UI shall remain responsive during agent processing. Long-running inference shall not block the browser interface.

### 6.2 Reliability

**NFR-R-01** The agent shall handle an `INSUFFICIENT` verdict from the critic and retry up to 3 times before returning a partial answer with a logged explanation.

**NFR-R-02** If ChromaDB is unavailable, the `semantic_search` tool shall fall back to TF-IDF without crashing the agent.

**NFR-R-03** If the Ollama server is offline, the UI shall display a clear error state in the sidebar chip and in the response area rather than hanging indefinitely.

### 6.3 Offline Operation

**NFR-O-01** After initial setup (model downloads, database generation), the system shall operate with no internet connection.

**NFR-O-02** No user data, queries, results, or model outputs shall be transmitted outside the local machine under any circumstances.

### 6.4 Maintainability

**NFR-M-01** The structured output schema (`IshikawaAnalysis`) shall be defined as a Pydantic v2 model to enforce type safety and allow schema evolution with backward-compatible validation.

**NFR-M-02** SQL safety shall be enforced at two layers — `sqlglot` AST parsing and regex injection guards — so that either layer alone is sufficient to block write operations.

---

## 7. Data Requirements

### 7.1 Database Overview

The system uses a single DuckDB file (`noruh_quality.db`, approximately 92 MB) containing four tables of synthetic factory history spanning five years.

| Table | Rows | Description |
|-------|------|-------------|
| `cnc_telemetry` | 657,360 | Per-part CNC machine sensor readings (vibration, temperature, spindle load, dimensional deviation) |
| `lab_testing` | 656,083 | CMM dimensional and surface finish test results (Ra, Rz, pass/fail flags, gouge flags) |
| `packaging_log` | 218,230 | Packaging line pass/fail records per station and shift |
| `customer_feedback` | 10,838 | Warranty claims and free-text complaint descriptions |

### 7.2 Five Injected Anomalies

The dataset contains five deliberate anomalies that the agent must be capable of identifying:

| Anomaly ID | Period | Description |
|------------|--------|-------------|
| ANOM-01 | April–June 2022 | Machine B calibration drift — dimensional deviation ramps from 0.01 mm to 0.25 mm |
| ANOM-02 | June–August 2023 | Cheap tooling procurement campaign — surface roughness (Ra) elevated to 2.4× baseline |
| ANOM-03 | October 2024 | New operator OP-007 gouge events — 76 `FAIL_GOUGE` parts at approximately 6% rate |
| ANOM-04 | Ongoing | Tool-breakage inline scrap — 1,277 rejections caused by vibration exceeding 3.5 g |
| ANOM-05 | 1–14 November 2025 | PKG-003 packaging station missing hardware — 64 customer claims at approximately 8% rate |

### 7.3 Vector Store

Customer feedback text from `customer_feedback` is embedded using the BAAI/bge-small-en-v1.5 model (512-dimensional normalised vectors) and persisted in a ChromaDB collection (`chroma_db/`). The vector store is built automatically on first application launch.

### 7.4 Data Generation

The database is generated by an automated script included in the project. Generation takes approximately 80 seconds on reference hardware. The resulting data is entirely synthetic and contains no real personal information.

### 7.5 Access Mode

The DuckDB database is opened in read-only mode. No application code path writes to the database during operation.

---

## 8. AI / LLM Requirements

### 8.1 Model Configuration

| Role | Model ID | Disk Size | Purpose |
|------|----------|-----------|---------|
| Tool-Calling Engine | `qwen3-coder:7b` | ~4.7 GB | SQL generation, tool orchestration, Ishikawa JSON output |
| Critic / Reasoning Engine | `deepseek-r1:8b` | ~4.9 GB | Evidence audit, SUFFICIENT/INSUFFICIENT verdict, `<think>` chain-of-thought |

Both models are served by Ollama on `localhost:11434`.

### 8.2 Sequential Loading

**LLM-01** The two models shall never be loaded into RAM simultaneously. The `tool_caller` node calls `qwen3-coder:7b`; after that call completes, Ollama evicts the model (`keep_alive: 0`). The `critic` node then calls `deepseek-r1:8b`; it is likewise evicted after the call. This pattern keeps peak RAM ≤ 12 GB on a 16 GB machine.

### 8.3 Inference Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `temperature` | 0.1 (both models) | Deterministic, factual output for diagnostic reasoning |
| `keep_alive` | 0 (both models) | Immediate eviction after each call to free RAM |

### 8.4 Retry Logic

**LLM-02** If the critic returns `INSUFFICIENT`, the agent shall loop back to `tool_caller` with a refined context. The maximum number of self-correction passes is **3**. If the critic has not returned `SUFFICIENT` after 3 passes, the `ishikawa_formatter` shall process the best available evidence and note the limitation in the `summary` field.

### 8.5 Output Parsing

**LLM-03** The `qwen3-coder:7b` model output for the final Ishikawa analysis shall be parsed and validated against the `IshikawaAnalysis` Pydantic v2 schema before being returned to the UI. Validation failures shall be caught and reported as structured errors rather than raw exceptions.

---

## 9. Security Requirements

### 9.1 SQL Injection Prevention

**SEC-01** All SQL strings generated by the LLM shall be validated through `sqlglot` AST parsing before execution. Any statement that is not a `SELECT` shall be rejected.

**SEC-02** A secondary regex-based guard shall block strings containing any of the following keywords regardless of AST parse results: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`.

**SEC-03** The DuckDB connection shall be opened with the `read_only=True` flag, providing a third layer of write protection at the database driver level.

### 9.2 Data Privacy

**SEC-04** No network calls shall be made to any external host during normal operation. All LLM inference, database queries, and vector search are local.

**SEC-05** No user query, database result, or model output shall be logged to any location accessible outside the local machine.

### 9.3 Model Integrity

**SEC-06** Models are downloaded from Ollama's official registry during setup and are not modified at runtime. The agent has no capability to modify model weights.

---

## 10. Deployment Requirements

### 10.1 Supported Platforms

- Windows 10 / Windows 11
- macOS (Intel and Apple Silicon)
- Linux (Ubuntu 20.04 LTS or later recommended)

### 10.2 Hardware Requirements (Minimum)

| Resource | Minimum |
|----------|---------|
| RAM | 16 GB |
| Free disk space | 20 GB |
| CPU | Any modern x86-64 or ARM64 |
| GPU | Not required — CPU-only inference |
| Internet (after setup) | Not required |

### 10.3 Software Dependencies

| Dependency | Purpose |
|------------|---------|
| Python 3.10+ | Runtime environment |
| Streamlit | Web dashboard framework |
| LangGraph | Agent state machine orchestration |
| Ollama | Local LLM server (localhost:11434) |
| DuckDB | Embedded SQL database |
| ChromaDB | Vector store |
| BAAI/bge-small-en-v1.5 | Sentence embedding model |
| sqlglot | SQL AST parsing for injection prevention |
| Pydantic v2 | Output schema validation |

### 10.4 Setup Time (One-Time)

| Step | Estimated Time |
|------|----------------|
| Python package installation | ~15 minutes |
| Ollama model downloads (~8.4 GB total) | 30–90 minutes (internet speed dependent) |
| Database generation | ~80 seconds |

### 10.5 Launch Method

On Windows, the application is launched by double-clicking `start_windows.bat`. On macOS/Linux, it is launched from the terminal with `streamlit run app.py`. The Streamlit server starts at `http://localhost:8501` and opens automatically in the default browser.

---

## 11. Out of Scope

The following capabilities are deliberately excluded from v2.0:

- **Live production system integration.** The agent reads only from its local DuckDB snapshot. It has no connection to live PLCs, MES systems, ERP databases, or IoT streams.
- **Corrective action.** The agent diagnoses; it does not write to any system, raise work orders, or trigger alerts.
- **Multi-user / networked operation.** The system is designed for single-user, single-machine use. No authentication, access control, or network server functionality is included.
- **Internet-connected LLM providers.** The system exclusively uses locally served Ollama models. OpenAI, Anthropic, Google, or other cloud APIs are not used.
- **Real-time data ingestion.** The database is a static snapshot. It is not updated by ongoing production.
- **Export or reporting.** The system does not generate PDF reports, spreadsheet exports, or email summaries.
- **Model fine-tuning.** The base Ollama models are used without modification or domain fine-tuning.
- **Historical conversation persistence.** Conversation history is maintained within a session only; it is not saved across sessions.

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **CMM** | Coordinate Measuring Machine — precision instrument used to measure the geometry of physical parts |
| **ChromaDB** | Open-source vector database used to store and retrieve semantic embeddings |
| **DuckDB** | Embedded analytical SQL database; runs in-process with no separate server |
| **Ishikawa analysis** | Also called a fishbone or cause-and-effect diagram. A structured quality tool that organises root causes into categories (Machine, Material, Method, Human/Environment) |
| **LangGraph** | Python library for building stateful, multi-step AI agent workflows as directed graphs |
| **LLM** | Large Language Model — a neural network trained to understand and generate text |
| **Ollama** | Open-source tool that serves LLMs locally via a REST API on localhost |
| **Pydantic v2** | Python library for data validation using type annotations |
| **Ra** | Arithmetic mean surface roughness — a measure of surface finish quality |
| **sqlglot** | Python library for SQL parsing and AST analysis |
| **TF-IDF** | Term Frequency–Inverse Document Frequency — a classical text similarity method used as fallback when vector embeddings are unavailable |
| **Vector store** | Database that stores high-dimensional numerical embeddings and supports similarity search |
| **ANOM-01 … ANOM-05** | The five deliberately injected data anomalies in the synthetic database (see Section 7.2) |
