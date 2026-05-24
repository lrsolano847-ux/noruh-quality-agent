"""
Multi-agent local reasoning engine for Noruh Manufacturing quality analysis.

Architecture (per PRD Section 2.3):
  Tool-Calling Engine  (qwen3-coder:7b)  — generates SQL + semantic searches
  Refining Thinking Engine (deepseek-r1:8b) — critiques results, decides retry/done
  Master Orchestrator  (LangGraph)       — state machine, 3-pass correction limit

Sequential model loading: keep_alive=0 evicts each model after its call,
keeping peak RAM within the 12 GB constraint.
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Generator, TypedDict, Annotated

from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from database import NoruhDB

# ── Ollama config ─────────────────────────────────────────────────────────────
OLLAMA_URL        = "http://localhost:11434"
TOOL_MODEL        = "qwen3-coder:7b"   # SQL generation + tool calling
CRITIC_MODEL      = "deepseek-r1:8b"   # Reasoning critique
MAX_RETRIES       = 3
MAX_SQL_ROWS      = 200                # cap result size sent to LLM context

# ─────────────────────────────────────────────────────────────────────────────
# LangGraph state
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages:        Annotated[list, add_messages]
    retry_count:     int
    tool_results:    list[dict]          # accumulated tool outputs
    ishikawa:        dict                # final structured output
    error:           str | None

# ─────────────────────────────────────────────────────────────────────────────
# Ishikawa output schema
# ─────────────────────────────────────────────────────────────────────────────

class IshikawaAnalysis(BaseModel):
    """Structured root-cause analysis mapped to Ishikawa fishbone categories."""
    material:          list[str] = Field(default_factory=list,
        description="Root causes related to raw material or tooling quality.")
    machine:           list[str] = Field(default_factory=list,
        description="Root causes related to CNC machine calibration or wear.")
    method:            list[str] = Field(default_factory=list,
        description="Root causes related to process parameters or procedures.")
    human_environment: list[str] = Field(default_factory=list,
        description="Root causes related to operator error or environment.")
    summary:           str = Field(default="",
        description="Executive summary of the full root-cause investigation.")
    anomalies_found:   list[str] = Field(default_factory=list,
        description="Named anomalies identified (e.g. ANOM-01, ANOM-02).")

# ─────────────────────────────────────────────────────────────────────────────
# Tool factory — bound to a NoruhDB instance at graph-build time
# ─────────────────────────────────────────────────────────────────────────────

def make_tools(db: NoruhDB):
    @tool
    def execute_sql(sql: str) -> str:
        """
        Execute a read-only SQL query against the Noruh Manufacturing DuckDB database.
        Returns results as a JSON array (capped at 200 rows).
        Use this for statistical aggregations, time-series trends, and join queries
        across cnc_telemetry, lab_testing, packaging_log, and customer_feedback.
        """
        try:
            rows = db.execute_sql(sql)
            rows = rows[:MAX_SQL_ROWS]
            return json.dumps(rows, default=str)
        except Exception as exc:
            return f"ERROR: {exc}"

    @tool
    def semantic_search(query: str, n_results: int = 10) -> str:
        """
        Search customer feedback text by semantic meaning using the local vector store.
        Returns the top matching complaint texts with similarity scores and categories.
        Use this to find complaint patterns, validate hypotheses about failure modes,
        or pull representative customer quotes for the root-cause narrative.
        """
        try:
            hits = db.semantic_search(query, n_results=min(n_results, 20))
            return json.dumps(hits, default=str)
        except Exception as exc:
            return f"ERROR: {exc}"

    return [execute_sql, semantic_search]

# ─────────────────────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────────────────────

def _tool_system_prompt(schema: str) -> str:
    return textwrap.dedent(f"""
        You are a precision manufacturing data analyst for Noruh Manufacturing,
        makers of premium stainless steel modular end tables (Top, Leg, Stand).

        Your job is to investigate quality anomalies by querying the operational
        database and customer feedback vector store. Use the available tools to
        gather statistical evidence, then synthesise your findings.

        DATABASE SCHEMA:
        {schema}

        INVESTIGATION STRATEGY:
        1. Start with time-series aggregations to identify when defect rates spiked.
        2. Join cnc_telemetry with lab_testing to correlate process parameters with
           quality outcomes (vibration, tool_age, feed_rate, spindle_speed).
        3. Trace confirmed bad parts through packaging_log to customer_feedback.
        4. Use semantic_search to find complaint patterns that match your hypothesis.
        5. After gathering data, classify root causes into Ishikawa categories:
           Material | Machine | Method | Human/Environment.

        RULES:
        - Only use SELECT queries. Never attempt INSERT, UPDATE, DELETE, DROP, ALTER.
        - If a query returns 0 rows, adjust the date range or filter and retry.
        - Quote all string literals in SQL (e.g. 'Machine_B', 'FAIL_GOUGE').
        - Always finish with a structured JSON block tagged <ishikawa> ... </ishikawa>
          containing keys: material, machine, method, human_environment, summary,
          anomalies_found.  Values are lists of strings (or a string for summary).
    """).strip()


def _critic_system_prompt() -> str:
    return textwrap.dedent("""
        You are a senior quality engineering auditor reviewing an AI agent's
        manufacturing root-cause analysis.

        Your task:
        1. Read the investigation data gathered so far (SQL results + semantic hits).
        2. Check whether the evidence is SUFFICIENT to draw a confident conclusion.
        3. If gaps exist, state exactly what additional query or search would fill them.
        4. If the evidence is sufficient, confirm the analysis and validate the
           Ishikawa categorisation.

        Respond in this format:
        <verdict>SUFFICIENT | INSUFFICIENT</verdict>
        <critique>
        [Your detailed critique here. If INSUFFICIENT, specify the exact missing
         evidence and the query/search that would resolve it.]
        </critique>

        Be concise. Do not re-run queries yourself — only advise the tool-calling
        agent on what to do next.
    """).strip()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ollama(model: str, tools=None, **kwargs) -> ChatOllama:
    """Returns a ChatOllama client that evicts the model from RAM after the call."""
    params = dict(
        model=model,
        base_url=OLLAMA_URL,
        keep_alive=0,        # evict immediately → sequential loading
        temperature=0.1,
        **kwargs,
    )
    if tools:
        return ChatOllama(**params).bind_tools(tools)
    return ChatOllama(**params)


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_think(text: str) -> str:
    """Extract deepseek-r1 <think> block content (may be empty)."""
    return _extract_tag(text, "think") or ""


def _parse_ishikawa_json(text: str) -> dict | None:
    """Parse <ishikawa> JSON block from the tool-caller's final message."""
    raw = _extract_tag(text, "ishikawa")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Attempt lenient parse by stripping trailing commas
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            return json.loads(cleaned)
        except Exception:
            return None

# ─────────────────────────────────────────────────────────────────────────────
# Graph nodes
# ─────────────────────────────────────────────────────────────────────────────

def make_graph(db: NoruhDB) -> Any:
    tools      = make_tools(db)
    tool_map   = {t.name: t for t in tools}
    schema     = db.schema_info()

    # ── Node 1: Tool-calling agent (qwen3-coder:7b) ───────────────────────────
    def tool_caller(state: AgentState) -> dict:
        llm = _ollama(TOOL_MODEL, tools=tools)
        sys_msg = SystemMessage(content=_tool_system_prompt(schema))

        # Build message list: system + conversation history
        msgs = [sys_msg] + list(state["messages"])
        response = llm.invoke(msgs)
        return {"messages": [response]}

    # ── Node 2: Tool executor ─────────────────────────────────────────────────
    def tool_executor(state: AgentState) -> dict:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {}

        results   = list(state.get("tool_results", []))
        new_msgs  = []

        for tc in last.tool_calls:
            fn   = tool_map.get(tc["name"])
            if fn is None:
                output = f"ERROR: unknown tool '{tc['name']}'"
            else:
                try:
                    output = fn.invoke(tc["args"])
                except Exception as exc:
                    output = f"ERROR: {exc}"

            results.append({"tool": tc["name"], "args": tc["args"], "output": output})
            new_msgs.append(ToolMessage(content=output, tool_call_id=tc["id"]))

        return {"messages": new_msgs, "tool_results": results}

    # ── Node 3: Critic (deepseek-r1:8b) ──────────────────────────────────────
    def critic(state: AgentState) -> dict:
        llm = _ollama(CRITIC_MODEL)

        # Summarise accumulated evidence for the critic
        evidence_summary = _build_evidence_summary(state)
        critique_prompt  = (
            f"INVESTIGATION SO FAR (retry {state['retry_count']} / {MAX_RETRIES}):\n\n"
            f"{evidence_summary}\n\n"
            "Audit this investigation and return your verdict."
        )

        msgs = [
            SystemMessage(content=_critic_system_prompt()),
            HumanMessage(content=critique_prompt),
        ]
        response = llm.invoke(msgs)
        text     = response.content if hasattr(response, "content") else str(response)

        verdict  = _extract_tag(text, "verdict") or "INSUFFICIENT"
        critique = _extract_tag(text, "critique") or text
        think    = _extract_think(text)

        # Append critic feedback as a human message so tool-caller sees it
        feedback = (
            f"[CRITIC — retry {state['retry_count']}/{MAX_RETRIES}]\n"
            f"Verdict: {verdict}\n\n"
            f"Critique:\n{critique}"
        )
        if think:
            feedback = f"<think>\n{think}\n</think>\n\n" + feedback

        return {
            "messages":    [HumanMessage(content=feedback)],
            "retry_count": state["retry_count"] + 1,
        }

    # ── Node 4: Ishikawa formatter ────────────────────────────────────────────
    def ishikawa_formatter(state: AgentState) -> dict:
        # Try to parse from the last tool-caller message
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                text = msg.content if isinstance(msg.content, str) else ""
                parsed = _parse_ishikawa_json(text)
                if parsed:
                    try:
                        validated = IshikawaAnalysis(**parsed)
                        return {"ishikawa": validated.model_dump()}
                    except Exception:
                        pass
                break

        # Fallback: ask the tool model to format what it has
        llm  = _ollama(TOOL_MODEL)
        msgs = [
            SystemMessage(content=(
                "Format the investigation findings as a JSON object with keys: "
                "material, machine, method, human_environment, summary, anomalies_found. "
                "Wrap it in <ishikawa> ... </ishikawa> tags. "
                "Be precise and manufacturing-specific."
            )),
            HumanMessage(content=_build_evidence_summary(state)),
        ]
        resp   = llm.invoke(msgs)
        text   = resp.content if hasattr(resp, "content") else str(resp)
        parsed = _parse_ishikawa_json(text)

        if parsed:
            try:
                validated = IshikawaAnalysis(**parsed)
                return {"ishikawa": validated.model_dump(), "messages": [resp]}
            except Exception:
                pass

        # Last resort: return raw text in summary
        return {
            "ishikawa": IshikawaAnalysis(summary=text).model_dump(),
            "messages": [resp],
        }

    # ── Conditional routing ───────────────────────────────────────────────────

    def after_tool_caller(state: AgentState) -> str:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage):
            return "end"
        # If model made tool calls → execute them
        if last.tool_calls:
            return "execute_tools"
        # If model included <ishikawa> block → format and finish
        text = last.content if isinstance(last.content, str) else ""
        if "<ishikawa>" in text:
            return "format_ishikawa"
        # Otherwise send to critic for review
        return "critic"

    def after_critic(state: AgentState) -> str:
        if state["retry_count"] >= MAX_RETRIES:
            return "format_ishikawa"    # exhausted retries → format what we have
        # Check critic's last message for verdict
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage) and "[CRITIC" in msg.content:
                if "SUFFICIENT" in msg.content and "INSUFFICIENT" not in msg.content:
                    return "format_ishikawa"
                return "tool_caller"   # retry with critic's guidance
        return "tool_caller"

    # ── Build graph ───────────────────────────────────────────────────────────
    graph = StateGraph(AgentState)

    graph.add_node("tool_caller",       tool_caller)
    graph.add_node("tool_executor",     tool_executor)
    graph.add_node("critic",            critic)
    graph.add_node("ishikawa_formatter",ishikawa_formatter)

    graph.set_entry_point("tool_caller")

    graph.add_conditional_edges(
        "tool_caller",
        after_tool_caller,
        {
            "execute_tools":   "tool_executor",
            "critic":          "critic",
            "format_ishikawa": "ishikawa_formatter",
            "end":             END,
        },
    )
    graph.add_edge("tool_executor", "tool_caller")

    graph.add_conditional_edges(
        "critic",
        after_critic,
        {
            "tool_caller":     "tool_caller",
            "format_ishikawa": "ishikawa_formatter",
        },
    )
    graph.add_edge("ishikawa_formatter", END)

    return graph.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Evidence summariser (for critic context)
# ─────────────────────────────────────────────────────────────────────────────

def _build_evidence_summary(state: AgentState) -> str:
    parts = []
    for tr in state.get("tool_results", []):
        tool_name = tr["tool"]
        args      = json.dumps(tr["args"], default=str)
        output    = tr["output"]
        # Truncate very long SQL results for the critic context
        if len(output) > 2000:
            output = output[:2000] + "\n... [truncated]"
        parts.append(f"TOOL: {tool_name}\nARGS: {args}\nRESULT:\n{output}")

    # Include the last tool-caller prose (non-tool-call content)
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            text = msg.content if isinstance(msg.content, str) else ""
            if text.strip():
                parts.append(f"AGENT ANALYSIS:\n{text}")
                break

    return "\n\n---\n\n".join(parts) if parts else "No evidence gathered yet."


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

class NoruhAgent:
    """
    High-level wrapper around the compiled LangGraph agent.
    Exposes run() for direct invocation and stream() for Streamlit rendering.
    """

    def __init__(
        self,
        db: NoruhDB,
        ollama_url: str = OLLAMA_URL,
    ) -> None:
        self._db    = db
        self._graph = make_graph(db)

    def run(self, question: str) -> IshikawaAnalysis:
        """Invoke the agent synchronously and return the Ishikawa analysis."""
        initial: AgentState = {
            "messages":     [HumanMessage(content=question)],
            "retry_count":  0,
            "tool_results": [],
            "ishikawa":     {},
            "error":        None,
        }
        final = self._graph.invoke(initial)
        raw   = final.get("ishikawa", {})
        return IshikawaAnalysis(**raw) if raw else IshikawaAnalysis(summary="No result.")

    def stream(self, question: str) -> Generator[dict, None, None]:
        """
        Stream agent events for Streamlit st.status() rendering.
        Yields dicts with keys: type, node, content
          type: 'node_start' | 'tool_call' | 'tool_result' | 'critic' | 'final'
        """
        initial: AgentState = {
            "messages":     [HumanMessage(content=question)],
            "retry_count":  0,
            "tool_results": [],
            "ishikawa":     {},
            "error":        None,
        }

        for event in self._graph.stream(initial, stream_mode="updates"):
            for node, update in event.items():
                if node == "tool_caller":
                    msgs = update.get("messages", [])
                    for m in msgs:
                        if isinstance(m, AIMessage):
                            if m.tool_calls:
                                for tc in m.tool_calls:
                                    yield {
                                        "type":    "tool_call",
                                        "node":    node,
                                        "tool":    tc["name"],
                                        "args":    tc["args"],
                                        "content": f"Calling {tc['name']}...",
                                    }
                            else:
                                yield {
                                    "type":    "analysis",
                                    "node":    node,
                                    "content": m.content or "",
                                }

                elif node == "tool_executor":
                    results = update.get("tool_results", [])
                    for tr in results[-1:]:   # only the newest result
                        yield {
                            "type":    "tool_result",
                            "node":    node,
                            "tool":    tr["tool"],
                            "content": tr["output"][:500],  # preview
                        }

                elif node == "critic":
                    msgs = update.get("messages", [])
                    for m in msgs:
                        content = m.content if hasattr(m, "content") else str(m)
                        yield {
                            "type":    "critic",
                            "node":    node,
                            "content": content,
                            "retry":   update.get("retry_count", 0),
                        }

                elif node == "ishikawa_formatter":
                    ishikawa = update.get("ishikawa", {})
                    yield {
                        "type":    "final",
                        "node":    node,
                        "content": ishikawa,
                    }


# ─────────────────────────────────────────────────────────────────────────────
# Connectivity check (called by app.py on startup)
# ─────────────────────────────────────────────────────────────────────────────

def check_ollama(url: str = OLLAMA_URL) -> tuple[bool, str]:
    """Returns (ok, message) — used by app.py to gate the UI."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as resp:
            data  = json.loads(resp.read())
            names = [m["name"] for m in data.get("models", [])]
            missing = [m for m in (TOOL_MODEL, CRITIC_MODEL) if m not in names]
            if missing:
                return False, (
                    f"Ollama running but missing models: {missing}. "
                    f"Run: ollama pull {' && ollama pull '.join(missing)}"
                )
            return True, f"Ollama ready. Models: {', '.join(names)}"
    except urllib.error.URLError:
        return False, (
            f"Ollama not reachable at {url}. "
            "Start it with: ollama serve"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke test (no Ollama required — just validates the graph compiles)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Validating agent graph construction ...")

    db = NoruhDB()
    agent = NoruhAgent(db)
    print("  Graph compiled successfully.")

    print("\nOllama connectivity check ...")
    ok, msg = check_ollama()
    print(f"  {'OK' if ok else 'OFFLINE'}: {msg}")

    if ok:
        print("\nRunning live diagnostic question ...")
        result = agent.run(
            "Investigate why we saw a spike in 'Fitment Issue' customer complaints "
            "during 2022. Identify the root cause and classify it using the "
            "Ishikawa framework."
        )
        print("\n── Ishikawa Analysis ──────────────────────────────────────────")
        print(f"Summary:           {result.summary}")
        print(f"Anomalies found:   {result.anomalies_found}")
        print(f"Machine causes:    {result.machine}")
        print(f"Method causes:     {result.method}")
        print(f"Material causes:   {result.material}")
        print(f"Human/Env causes:  {result.human_environment}")
    else:
        print("\nSkipping live run (Ollama offline). Graph structure is valid.")
        print("To run the full agent: start Ollama, then re-run this script.")
