"""
Noruh Manufacturing — Local Quality Analytics Agent
Streamlit engineering dashboard with real-time agent streaming.

Run with:  streamlit run app.py
"""

import json
import sys
from pathlib import Path

import streamlit as st

# Add project root to path so imports resolve from any working directory
sys.path.insert(0, str(Path(__file__).parent))

from database import NoruhDB
from agent import NoruhAgent, IshikawaAnalysis, check_ollama

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Noruh Quality Agent",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Ishikawa category cards */
.ishi-card {
    background: #1e1e2e;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 4px solid;
}
.ishi-machine  { border-color: #ef4444; }
.ishi-material { border-color: #f97316; }
.ishi-method   { border-color: #3b82f6; }
.ishi-human    { border-color: #22c55e; }
.ishi-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 6px;
}
.ishi-item {
    font-size: 0.9rem;
    padding: 3px 0;
    line-height: 1.5;
}
/* SQL preview block */
.sql-preview {
    font-family: monospace;
    font-size: 0.78rem;
    background: #0d1117;
    padding: 8px 12px;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-all;
    color: #7dd3fc;
}
/* Anomaly badge */
.anomaly-badge {
    display: inline-block;
    background: #7c3aed;
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 12px;
    margin: 2px 3px;
    letter-spacing: 0.05em;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session-state initialisation
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Connecting to manufacturing database …")
def load_db() -> NoruhDB:
    db = NoruhDB()
    db.build_vector_store()   # no-op if already built
    return db


@st.cache_resource(show_spinner="Initialising reasoning engine …")
def load_agent(_db: NoruhDB) -> NoruhAgent:
    return NoruhAgent(_db)


if "history" not in st.session_state:
    st.session_state.history = []   # list of {role, content, ishikawa?}


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — system status
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔩 Noruh Quality Agent")
    st.markdown("*Local • Offline • CPU-Only*")
    st.divider()

    # DB status
    db_path = Path("data/noruh_quality.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1_048_576
        st.success(f"**Database** connected ({size_mb:.1f} MB)")
    else:
        st.error("**Database** not found — run `python pipeline.py` first")
        st.stop()

    # Ollama status
    ok, msg = check_ollama()
    if ok:
        st.success("**Ollama** ready")
    else:
        st.warning(f"**Ollama** offline\n\n`{msg}`")

    # Vector store status
    chroma_path = Path("chroma_db")
    if chroma_path.exists() and any(chroma_path.iterdir()):
        st.success("**Vector store** loaded")
    else:
        st.info("**Vector store** will be built on first query")

    st.divider()

    # Example questions
    st.markdown("#### Example questions")
    EXAMPLES = [
        "Why did fitment complaints spike in Q2 2022?",
        "Investigate the surface finish issues from summer 2023.",
        "What caused the gouge defects in October 2024?",
        "Analyse the missing hardware claims from November 2025.",
        "Give me a full quality overview for Year 3 across all machines.",
    ]
    for q in EXAMPLES:
        if st.button(q, use_container_width=True, key=f"ex_{q[:20]}"):
            st.session_state["prefill"] = q

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

    st.markdown(
        "<small style='opacity:0.4'>All inference runs locally via Ollama.<br>"
        "No data leaves this machine.</small>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Load resources (cached)
# ─────────────────────────────────────────────────────────────────────────────

db    = load_db()
agent = load_agent(db)


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("# Noruh Manufacturing — Quality Analytics Agent")
st.markdown(
    "Ask any engineering question about the 5-year production history. "
    "The agent queries CNC telemetry, lab testing, packaging logs, and "
    "customer feedback to diagnose root causes using the Ishikawa framework."
)
st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Conversation history
# ─────────────────────────────────────────────────────────────────────────────

def _render_ishikawa(analysis: dict) -> None:
    """Render the Ishikawa fishbone analysis as structured cards."""
    a = IshikawaAnalysis(**analysis)

    # Anomaly badges
    if a.anomalies_found:
        badges = " ".join(
            f'<span class="anomaly-badge">{x}</span>' for x in a.anomalies_found
        )
        st.markdown(f"**Anomalies identified:** {badges}", unsafe_allow_html=True)

    # Summary box
    if a.summary:
        st.info(a.summary)

    # Four fishbone categories
    cats = [
        ("machine",           "Machine",           "ishi-machine",  "⚙️"),
        ("material",          "Material / Tooling","ishi-material", "🪛"),
        ("method",            "Method / Process",  "ishi-method",   "📋"),
        ("human_environment", "Human / Environment","ishi-human",   "👤"),
    ]

    cols = st.columns(2)
    for i, (key, label, css_cls, icon) in enumerate(cats):
        items = getattr(a, key, [])
        with cols[i % 2]:
            if items:
                items_html = "".join(
                    f'<div class="ishi-item">• {item}</div>' for item in items
                )
            else:
                items_html = '<div class="ishi-item" style="opacity:0.4">No factors identified</div>'

            st.markdown(
                f'<div class="ishi-card {css_cls}">'
                f'<div class="ishi-title">{icon} {label}</div>'
                f'{items_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry.get("ishikawa"):
            _render_ishikawa(entry["ishikawa"])


# ─────────────────────────────────────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────────────────────────────────────

prefill   = st.session_state.pop("prefill", "")
question  = st.chat_input(
    "Ask an engineering question about production quality …",
    key="chat_input",
)
if not question and prefill:
    question = prefill

if question:
    # Render user message
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.history.append({"role": "user", "content": question})

    # ── Agent run with streaming status ──────────────────────────────────────
    with st.chat_message("assistant"):

        if not ok:
            st.warning(
                "Ollama is not running. Start it with `ollama serve` and ensure "
                f"`qwen3-coder:7b` and `deepseek-r1:8b` are pulled."
            )
            st.session_state.history.append({
                "role": "assistant",
                "content": "⚠️ Ollama offline — cannot run agent.",
            })
        else:
            final_ishikawa = None
            final_summary  = ""

            with st.status("🔍 Investigating …", expanded=True) as status:
                retry_containers: dict[int, any] = {}
                current_retry = 0

                for event in agent.stream(question):
                    etype = event.get("type")

                    # ── Tool call ─────────────────────────────────────────────
                    if etype == "tool_call":
                        tool_name = event["tool"]
                        args      = event["args"]
                        if tool_name == "execute_sql":
                            sql = args.get("sql", "")
                            st.markdown(f"**SQL query**")
                            st.markdown(
                                f'<div class="sql-preview">{sql}</div>',
                                unsafe_allow_html=True,
                            )
                        elif tool_name == "semantic_search":
                            q = args.get("query", "")
                            st.markdown(f"**Semantic search:** _{q}_")

                    # ── Tool result ───────────────────────────────────────────
                    elif etype == "tool_result":
                        tool_name = event["tool"]
                        preview   = event["content"]
                        try:
                            rows = json.loads(preview)
                            if isinstance(rows, list):
                                st.caption(f"↳ {tool_name} returned {len(rows)} rows (preview)")
                            else:
                                st.caption(f"↳ {tool_name}: {str(rows)[:200]}")
                        except Exception:
                            st.caption(f"↳ {preview[:200]}")

                    # ── Analysis text (tool-caller prose) ────────────────────
                    elif etype == "analysis":
                        content = event.get("content", "")
                        if not content.strip():
                            pass
                        elif "<ishikawa>" in content:
                            # Collapsed expander — useful during prompt validation
                            # to see exactly what the model produced before parsing
                            with st.expander(
                                "🔍 Raw model output (Ishikawa block)", expanded=False
                            ):
                                st.code(content, language=None)
                        else:
                            st.markdown(f"**Agent analysis:**\n\n{content[:800]}")

                    # ── Critic feedback ───────────────────────────────────────
                    elif etype == "critic":
                        retry_num = event.get("retry", current_retry)
                        content   = event.get("content", "")

                        verdict  = "SUFFICIENT" if "SUFFICIENT" in content and "INSUFFICIENT" not in content else "INSUFFICIENT"
                        v_icon   = "✅" if verdict == "SUFFICIENT" else "🔄"

                        with st.expander(
                            f"{v_icon} Critic review — pass {retry_num}/{3}",
                            expanded=(verdict == "INSUFFICIENT"),
                        ):
                            # Strip think block for display
                            import re
                            display = re.sub(r"<think>.*?</think>", "", content,
                                            flags=re.DOTALL).strip()
                            st.markdown(display[:1500])

                        current_retry = retry_num

                    # ── Final Ishikawa output ─────────────────────────────────
                    elif etype == "final":
                        final_ishikawa = event.get("content", {})
                        if final_ishikawa.get("summary"):
                            final_summary = final_ishikawa["summary"]

                # Update status label on completion
                if final_ishikawa:
                    anomalies = final_ishikawa.get("anomalies_found", [])
                    label = f"✅ Investigation complete"
                    if anomalies:
                        label += f" — {', '.join(anomalies)} identified"
                    status.update(label=label, state="complete", expanded=False)
                else:
                    status.update(label="⚠️ Investigation incomplete", state="error")

            # ── Render Ishikawa output below the status container ─────────────
            if final_ishikawa:
                st.markdown("### Root-Cause Analysis")
                _render_ishikawa(final_ishikawa)

            # Persist to history
            st.session_state.history.append({
                "role":     "assistant",
                "content":  final_summary or "Investigation complete. See analysis below.",
                "ishikawa": final_ishikawa,
            })
