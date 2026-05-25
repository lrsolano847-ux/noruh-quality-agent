"""
Enterprise architecture diagram — Noruh Manufacturing Quality Agent.
Run: python generate_diagram.py
Output: noruh_architecture.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
from datetime import date

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 22, 15
fig, ax = plt.subplots(figsize=(W, H), dpi=180)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor("#ffffff")

# ── Design tokens ─────────────────────────────────────────────────────────────
NAVY      = "#0f172a"
NAVY_MID  = "#1e3a5f"
BLUE      = "#1d4ed8"
BLUE_LT   = "#dbeafe"
BLUE_MID  = "#3b82f6"
VIOLET    = "#5b21b6"
VIOLET_LT = "#ede9fe"
VIOLET_MID= "#7c3aed"
TEAL      = "#0f766e"
TEAL_LT   = "#ccfbf1"
TEAL_MID  = "#14b8a6"
AMBER     = "#92400e"
AMBER_LT  = "#fef3c7"
AMBER_MID = "#f59e0b"
SLATE     = "#334155"
SLATE_LT  = "#f1f5f9"
SLATE_MID = "#94a3b8"
RED       = "#dc2626"
GREEN     = "#16a34a"
WHITE     = "#ffffff"
DIVIDER   = "#e2e8f0"

# ── Helpers ───────────────────────────────────────────────────────────────────

def shadow(ax, x, y, w, h, radius=0.22, alpha=0.12, offset=0.07):
    s = FancyBboxPatch((x + offset, y - offset), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor="#000000", alpha=alpha, zorder=2,
                       linewidth=0)
    ax.add_patch(s)

def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.22, z=4):
    shadow(ax, x, y, w, h, radius)
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z)
    ax.add_patch(r)

def header_box(ax, x, y, w, h, fc, ec, lw=2, radius=0.22):
    shadow(ax, x, y, w, h, radius, alpha=0.15)
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=4)
    ax.add_patch(r)

def txt(ax, x, y, s, size=9, weight="normal", color=SLATE, ha="center",
        va="center", z=6, alpha=1.0, style="normal"):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color,
            ha=ha, va=va, zorder=z, alpha=alpha, style=style,
            fontfamily="DejaVu Sans")

def section_label(ax, x, y, s, color=WHITE):
    txt(ax, x, y, s, size=7.5, weight="bold", color=color,
        ha="left", va="center")

def arr(ax, x1, y1, x2, y2, color=SLATE_MID, lw=1.6,
        style="->", rad=0.0, label="", label_color=SLATE_MID):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle=style,
                    color=color,
                    lw=lw,
                    connectionstyle=f"arc3,rad={rad}",
                    shrinkA=4, shrinkB=4,
                ), zorder=5)
    if label:
        mx = (x1 + x2) / 2 + (0.15 if rad == 0 else 0)
        my = (y1 + y2) / 2
        txt(ax, mx, my, label, size=7, color=label_color, weight="bold")

def divider(ax, x1, x2, y, color=DIVIDER, lw=0.8, style="--"):
    ax.plot([x1, x2], [y, y], color=color, lw=lw,
            linestyle=style, zorder=3)

def pill(ax, x, y, w, h, fc, ec, label, lc=WHITE, size=7.5):
    r = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0,rounding_size=0.15",
                       facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=6)
    ax.add_patch(r)
    txt(ax, x + w/2, y + h/2, label, size=size, color=lc, weight="bold")


# ═════════════════════════════════════════════════════════════════════════════
# TITLE BLOCK
# ═════════════════════════════════════════════════════════════════════════════
box(ax, 0.3, 13.45, W - 0.6, 1.3, NAVY, NAVY, radius=0.3, lw=0)
txt(ax, W/2, 14.25, "NORUH MANUFACTURING — QUALITY ANALYTICS AGENT",
    size=15, weight="bold", color=WHITE)
txt(ax, W/2, 13.78,
    "Local · Offline · CPU-Only  |  LangGraph Multi-Agent Architecture  |  Ollama LLM Inference",
    size=9, color=SLATE_MID)

# Version badge
pill(ax, 18.8, 13.6, 2.8, 0.55, BLUE, BLUE, f"v2.0  ·  {date.today().strftime('%b %Y')}")

# ═════════════════════════════════════════════════════════════════════════════
# SWIM-LANE BACKGROUNDS
# ═════════════════════════════════════════════════════════════════════════════
# UI lane
r = FancyBboxPatch((0.3, 11.55), W - 0.6, 1.65,
                   boxstyle="round,pad=0,rounding_size=0.2",
                   facecolor=BLUE_LT, edgecolor=BLUE_MID,
                   linewidth=1.5, zorder=1, alpha=0.6)
ax.add_patch(r)

# Agent lane
r2 = FancyBboxPatch((0.3, 4.6), W - 0.6, 6.7,
                    boxstyle="round,pad=0,rounding_size=0.2",
                    facecolor=VIOLET_LT, edgecolor=VIOLET_MID,
                    linewidth=1.5, zorder=1, alpha=0.5)
ax.add_patch(r2)

# Infrastructure lane (split into two halves)
r3 = FancyBboxPatch((0.3, 0.35), 10.5, 4.0,
                    boxstyle="round,pad=0,rounding_size=0.2",
                    facecolor=AMBER_LT, edgecolor=AMBER_MID,
                    linewidth=1.5, zorder=1, alpha=0.5)
ax.add_patch(r3)

r4 = FancyBboxPatch((11.1, 0.35), W - 11.4, 4.0,
                    boxstyle="round,pad=0,rounding_size=0.2",
                    facecolor=TEAL_LT, edgecolor=TEAL_MID,
                    linewidth=1.5, zorder=1, alpha=0.5)
ax.add_patch(r4)

# Lane labels
section_label(ax, 0.6, 12.88, "USER INTERFACE", BLUE)
section_label(ax, 0.6, 11.1,  "AGENT ENGINE  (LangGraph Orchestration)", VIOLET)
section_label(ax, 0.6, 4.15,  "OLLAMA  (Local LLM Server · localhost:11434)", AMBER)
section_label(ax, 11.4, 4.15, "DATA LAYER  (NoruhDB)", TEAL)

# ═════════════════════════════════════════════════════════════════════════════
# UI LAYER — Streamlit Dashboard
# ═════════════════════════════════════════════════════════════════════════════
box(ax, 5.5, 11.75, 11, 1.15, WHITE, BLUE, lw=2)
txt(ax, 11, 12.6, "app.py  —  Streamlit Dashboard", size=11,
    weight="bold", color=BLUE)

# Sub-components in UI
ui_items = [
    ("Sidebar\nStatus Chips", 6.4, 12.05),
    ("Chat\nInput", 8.2, 12.05),
    ("st.status()\nStreaming Panel", 10.2, 12.05),
    ("Ishikawa\nCard Grid", 12.2, 12.05),
    ("Conversation\nHistory", 14.2, 12.05),
]
for label_text, cx, cy in ui_items:
    pill(ax, cx - 0.72, cy - 0.2, 1.44, 0.58,
         BLUE_LT, BLUE_MID, label_text, BLUE, 6.8)

# ═════════════════════════════════════════════════════════════════════════════
# AGENT LAYER
# ═════════════════════════════════════════════════════════════════════════════

# ── NoruhAgent wrapper ────────────────────────────────────────────────────────
box(ax, 0.7, 4.8, W - 1.4, 6.45, WHITE, VIOLET, lw=1.5, radius=0.25, z=3)
txt(ax, W/2, 11.0, "NoruhAgent  (agent.py)", size=10, weight="bold",
    color=VIOLET, z=6)

# ── LangGraph nodes ───────────────────────────────────────────────────────────
NODE_Y  = 9.05
NODE_H  = 1.55
NODE_W  = 4.0
NODE_XS = [1.0, 5.4, 9.8, 14.2]
NODE_TITLES = [
    "tool_caller",
    "tool_executor",
    "critic",
    "ishikawa_formatter",
]
NODE_SUBS = [
    "qwen3-coder:7b\nSQL · Tool calls · Ishikawa JSON",
    "Executes tools\nagainst real database",
    "deepseek-r1:8b\nSUFFICIENT / INSUFFICIENT",
    "Parses & validates\nIshikawaAnalysis (Pydantic)",
]
NODE_COLORS = [BLUE, VIOLET_MID, VIOLET, TEAL]

for i, (nx, nt, ns, nc) in enumerate(
        zip(NODE_XS, NODE_TITLES, NODE_SUBS, NODE_COLORS)):
    box(ax, nx, NODE_Y, NODE_W, NODE_H, WHITE, nc, lw=2.2, radius=0.2)
    # coloured top band
    band = FancyBboxPatch((nx, NODE_Y + NODE_H - 0.42), NODE_W, 0.42,
                          boxstyle="round,pad=0,rounding_size=0.2",
                          facecolor=nc, edgecolor=nc, lw=0, zorder=5)
    ax.add_patch(band)
    txt(ax, nx + NODE_W/2, NODE_Y + NODE_H - 0.21,
        nt, size=9.5, weight="bold", color=WHITE, z=6)
    txt(ax, nx + NODE_W/2, NODE_Y + 0.52,
        ns, size=8.2, color=SLATE, z=6)
    # node number badge
    pill(ax, nx + 0.1, NODE_Y + NODE_H - 0.32, 0.32, 0.32,
         WHITE, nc, str(i + 1), nc, 7)

# forward arrows between nodes
for i in range(3):
    arr(ax, NODE_XS[i] + NODE_W, NODE_Y + NODE_H/2,
        NODE_XS[i+1], NODE_Y + NODE_H/2,
        VIOLET_MID, lw=2.2)

# INSUFFICIENT retry arrow
ax.annotate("", xy=(NODE_XS[0] + NODE_W/2, NODE_Y),
            xytext=(NODE_XS[2] + NODE_W/2, NODE_Y),
            arrowprops=dict(arrowstyle="->", color=RED, lw=2,
                            connectionstyle="arc3,rad=0.38",
                            shrinkA=4, shrinkB=4), zorder=6)
txt(ax, 9.1, 8.18, "INSUFFICIENT  (max 3 retries)",
    size=7.5, color=RED, weight="bold")

# SUFFICIENT label
txt(ax, 16.5, NODE_Y + NODE_H/2 + 0.22, "SUFFICIENT", size=7.5,
    color=GREEN, weight="bold")

# ── AgentState ────────────────────────────────────────────────────────────────
box(ax, 1.0, 5.2, 5.0, 3.55, SLATE_LT, VIOLET_MID, lw=1.5, radius=0.18)
txt(ax, 3.5, 8.47, "AgentState", size=9, weight="bold", color=VIOLET)
state_fields = [
    ("messages",      "Conversation + tool history"),
    ("tool_results",  "SQL & search outputs"),
    ("retry_count",   "0 → 3 passes"),
    ("ishikawa",      "Final structured output"),
    ("error",         "Exception capture"),
]
for j, (fname, fdesc) in enumerate(state_fields):
    y = 8.1 - j * 0.54
    txt(ax, 1.55, y, fname, size=8, weight="bold", color=VIOLET_MID, ha="left")
    txt(ax, 1.55, y - 0.24, fdesc, size=7.2, color=SLATE_MID, ha="left")

# ── Tools ─────────────────────────────────────────────────────────────────────
box(ax, 6.5, 5.2, 5.0, 3.55, SLATE_LT, BLUE, lw=1.5, radius=0.18)
txt(ax, 9.0, 8.47, "Tools  (database.py)", size=9, weight="bold", color=BLUE)

tool_items = [
    ("execute_sql(sql)",
     "Read-only DuckDB query",
     "sqlglot AST + regex injection guard"),
    ("semantic_search(query, n)",
     "ChromaDB cosine similarity",
     "BAAI/bge-small-en-v1.5 embeddings"),
]
for j, (tname, tdesc, tnote) in enumerate(tool_items):
    y = 8.0 - j * 1.5
    txt(ax, 7.0, y, tname, size=8.5, weight="bold", color=BLUE, ha="left")
    txt(ax, 7.0, y - 0.32, tdesc, size=7.8, color=SLATE, ha="left")
    txt(ax, 7.0, y - 0.62, tnote, size=7, color=SLATE_MID, ha="left",
        style="italic")

# ── IshikawaAnalysis schema ───────────────────────────────────────────────────
box(ax, 12.0, 5.2, 5.6, 3.55, SLATE_LT, TEAL, lw=1.5, radius=0.18)
txt(ax, 14.8, 8.47, "IshikawaAnalysis  (Pydantic v2)",
    size=9, weight="bold", color=TEAL)
schema_fields = [
    ("machine",           "list[str]",  "CNC / equipment root causes"),
    ("material",          "list[str]",  "Tooling / material root causes"),
    ("method",            "list[str]",  "Process / procedure root causes"),
    ("human_environment", "list[str]",  "Operator / environment factors"),
    ("summary",           "str",        "Executive narrative"),
    ("anomalies_found",   "list[str]",  "e.g. ANOM-01 … ANOM-05"),
]
for j, (fn, ft, fd) in enumerate(schema_fields):
    y = 8.08 - j * 0.47
    txt(ax, 12.5, y, fn, size=7.8, weight="bold", color=TEAL, ha="left")
    txt(ax, 15.4, y, ft, size=7.2, color=TEAL_MID, ha="left")
    txt(ax, 12.5, y - 0.23, fd, size=7, color=SLATE_MID, ha="left")

# ═════════════════════════════════════════════════════════════════════════════
# OLLAMA LAYER — two model cards
# ═════════════════════════════════════════════════════════════════════════════
for i, (model, role, role2, details, color, xoff) in enumerate([
    ("qwen3-coder:7b",
     "Tool-Calling Engine",
     "SQL generation · Tool orchestration · Ishikawa JSON",
     ["Temperature: 0.1", "keep_alive: 0 (evicted after call)",
      "Context: schema + conversation", "~4.7 GB on disk"],
     BLUE, 0.7),
    ("deepseek-r1:8b",
     "Critic / Reasoning Engine",
     "Evidence audit · SUFFICIENT/INSUFFICIENT verdict · <think> reasoning",
     ["Temperature: 0.1", "keep_alive: 0 (evicted after call)",
      "Input: evidence summary", "~4.9 GB on disk"],
     VIOLET, 5.7),
]):
    box(ax, xoff, 0.6, 4.7, 3.3, WHITE, color, lw=2, radius=0.22)
    # top band
    band = FancyBboxPatch((xoff, 0.6 + 3.3 - 0.5), 4.7, 0.5,
                          boxstyle="round,pad=0,rounding_size=0.22",
                          facecolor=color, edgecolor=color, lw=0, zorder=5)
    ax.add_patch(band)
    txt(ax, xoff + 2.35, 0.6 + 3.3 - 0.25, model,
        size=10, weight="bold", color=WHITE, z=6)
    txt(ax, xoff + 2.35, 0.6 + 2.62, role,
        size=8.5, weight="bold", color=color, z=6)
    txt(ax, xoff + 2.35, 0.6 + 2.2, role2, size=7.5, color=SLATE, z=6)
    for k, d in enumerate(details):
        txt(ax, xoff + 0.25, 0.6 + 1.65 - k * 0.37, f"• {d}",
            size=7.5, color=SLATE_MID, ha="left", z=6)

# Sequential loading note
box(ax, 0.7, 0.38, 10.1, 0.22, AMBER_LT, AMBER_MID, lw=1, radius=0.08)
txt(ax, 5.75, 0.49,
    "Sequential loading: models are evicted from RAM after each call "
    "— peak RAM ≤ 12 GB on 16 GB machine",
    size=7.2, color=AMBER, weight="bold")

# ═════════════════════════════════════════════════════════════════════════════
# DATA LAYER — DuckDB + ChromaDB
# ═════════════════════════════════════════════════════════════════════════════
DB_XS = [11.3, 16.5]
DB_LABELS = ["DuckDB", "ChromaDB"]
DB_SUBS   = ["noruh_quality.db  (~92 MB)", "Vector Store  (chroma_db/)"]
DB_COLORS = [TEAL, TEAL_MID]
DB_DETAILS = [
    ["cnc_telemetry       ~657,000 rows",
     "lab_testing          ~655,000 rows",
     "packaging_log       ~218,000 rows",
     "customer_feedback   10,838 rows",
     "─────────────────────────────",
     "5 injected anomalies · 5-year history",
     "ANOM-01 → ANOM-05"],
    ["10,838 customer feedback docs",
     "BAAI/bge-small-en-v1.5 embeddings",
     "TF-IDF fallback (offline mode)",
     "Cosine similarity retrieval",
     "Persisted to disk (chroma_db/)",
     "Built on first app launch",
     "512-dim normalised vectors"],
]
for i, (dx, dl, ds, dc, dd) in enumerate(
        zip(DB_XS, DB_LABELS, DB_SUBS, DB_COLORS, DB_DETAILS)):
    box(ax, dx, 0.6, 4.9, 3.3, WHITE, dc, lw=2, radius=0.22)
    band = FancyBboxPatch((dx, 0.6 + 3.3 - 0.5), 4.9, 0.5,
                          boxstyle="round,pad=0,rounding_size=0.22",
                          facecolor=dc, edgecolor=dc, lw=0, zorder=5)
    ax.add_patch(band)
    txt(ax, dx + 2.45, 0.6 + 3.3 - 0.25, dl,
        size=10, weight="bold", color=WHITE, z=6)
    txt(ax, dx + 2.45, 0.6 + 2.65, ds,
        size=8, weight="bold", color=dc, z=6)
    for k, d in enumerate(dd):
        txt(ax, dx + 0.2, 0.6 + 2.25 - k * 0.31, d if d.startswith("─") else f"• {d}",
            size=7.2, color=SLATE_MID if d.startswith("─") else SLATE,
            ha="left", z=6, style="normal" if not d.startswith("─") else "italic")

# ═════════════════════════════════════════════════════════════════════════════
# INTER-LAYER CONNECTIONS
# ═════════════════════════════════════════════════════════════════════════════

# User → Streamlit
arr(ax, 11, 13.2, 11, 12.9, BLUE, lw=2, label="question", label_color=BLUE)

# Streamlit → Agent (stream call)
arr(ax, 11, 11.75, 11, 11.25, BLUE, lw=2, label="agent.stream()", label_color=BLUE)

# tool_caller → Ollama (qwen)
arr(ax, 2.3, NODE_Y, 2.3, 4.0, BLUE_MID, lw=1.8, label="inference", label_color=BLUE_MID)

# critic → Ollama (deepseek)
arr(ax, 11.8, NODE_Y, 7.05, 4.0, VIOLET_MID, lw=1.8, label="inference", label_color=VIOLET_MID)

# tool_executor → DuckDB
arr(ax, 7.4, NODE_Y, 13.0, 4.0, TEAL, lw=1.8, label="execute_sql()", label_color=TEAL)

# tool_executor → ChromaDB
arr(ax, 8.0, NODE_Y, 18.0, 4.0, TEAL_MID, lw=1.8, label="semantic_search()", label_color=TEAL_MID)

# ishikawa_formatter → Streamlit
arr(ax, 18.2, NODE_Y + NODE_H, 15.5, 11.75, VIOLET, lw=1.8,
    label="stream events", label_color=VIOLET)

# ═════════════════════════════════════════════════════════════════════════════
# LEGEND
# ═════════════════════════════════════════════════════════════════════════════
LEG_X, LEG_Y = 0.45, 4.62
box(ax, LEG_X, LEG_Y, 4.5, 4.05, WHITE, DIVIDER, lw=1, radius=0.15)
txt(ax, LEG_X + 2.25, LEG_Y + 3.75, "LEGEND",
    size=8.5, weight="bold", color=SLATE)

legend_items = [
    (BLUE,       "User Interface  (Streamlit)"),
    (VIOLET,     "Agent Engine  (LangGraph)"),
    (AMBER,      "LLM Inference  (Ollama)"),
    (TEAL,       "Data Layer  (DuckDB · ChromaDB)"),
    (RED,        "Retry path  (INSUFFICIENT)"),
    (GREEN,      "Success path  (SUFFICIENT)"),
]
for k, (lc, ll) in enumerate(legend_items):
    cy = LEG_Y + 3.3 - k * 0.52
    pill(ax, LEG_X + 0.2, cy - 0.14, 0.48, 0.3, lc, lc, "", lc)
    txt(ax, LEG_X + 0.88, cy, ll, size=7.8, color=SLATE, ha="left")

# ── Footnote ─────────────────────────────────────────────────────────────────
txt(ax, W/2, 0.16,
    f"Noruh Manufacturing Quality Agent  ·  Architecture v2.0  ·  {date.today().strftime('%B %Y')}  "
    "·  All inference runs locally — no data leaves the machine",
    size=7.2, color=SLATE_MID)

plt.tight_layout(pad=0)
plt.savefig("noruh_architecture.png", dpi=180, bbox_inches="tight",
            facecolor=WHITE)
print("Saved noruh_architecture.png")
