"""Generate architecture diagram for the Noruh Quality Agent."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

fig, ax = plt.subplots(1, 1, figsize=(18, 13))
ax.set_xlim(0, 18)
ax.set_ylim(0, 13)
ax.axis("off")
fig.patch.set_facecolor("#f8fafc")

# ── Colour palette ────────────────────────────────────────────────────────────
C = {
    "ui":       "#dbeafe",   # blue-100
    "ui_bdr":   "#3b82f6",   # blue-500
    "agent":    "#ede9fe",   # violet-100
    "agent_bdr":"#7c3aed",   # violet-700
    "node":     "#f5f3ff",   # violet-50
    "node_bdr": "#a78bfa",   # violet-400
    "ollama":   "#fef3c7",   # amber-100
    "ollama_bdr":"#d97706",  # amber-600
    "model":    "#fffbeb",   # amber-50
    "model_bdr":"#fbbf24",   # amber-400
    "data":     "#dcfce7",   # green-100
    "data_bdr": "#16a34a",   # green-600
    "db":       "#f0fdf4",   # green-50
    "db_bdr":   "#4ade80",   # green-400
    "arrow":    "#64748b",   # slate-500
    "text":     "#1e293b",   # slate-900
    "muted":    "#64748b",   # slate-500
}


def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.25):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={radius}",
                          facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(rect)


def label(ax, x, y, text, size=10, weight="normal", color="#1e293b", ha="center", va="center"):
    ax.text(x, y, text, fontsize=size, fontweight=weight,
            color=color, ha=ha, va=va, zorder=5)


def arrow(ax, x1, y1, x2, y2, color="#64748b", lw=1.5, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"),
                zorder=4)


def section_bg(ax, x, y, w, h, fc, ec, title, title_color):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0,rounding_size=0.35",
                          facecolor=fc, edgecolor=ec, linewidth=2, zorder=1)
    ax.add_patch(rect)
    ax.text(x + 0.18, y + h - 0.22, title, fontsize=8.5, fontweight="bold",
            color=title_color, ha="left", va="top", zorder=5)


# ═══════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════
ax.text(9, 12.65, "Noruh Manufacturing Quality Agent — Architecture",
        fontsize=15, fontweight="bold", color=C["text"], ha="center", va="center")
ax.text(9, 12.3, "Local · Offline · CPU-Only",
        fontsize=9, color=C["muted"], ha="center", va="center")

# ═══════════════════════════════════════════════════════════════════
# LAYER 1 — USER INTERFACE  (top)
# ═══════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 10.6, 17.2, 1.5, C["ui"], C["ui_bdr"],
           "UI LAYER", C["ui_bdr"])

box(ax, 5.5, 10.85, 7, 0.95, C["ui"], C["ui_bdr"], lw=2)
label(ax, 9, 11.45, "app.py", 10, "bold", C["ui_bdr"])
label(ax, 9, 11.12,
      "Streamlit Dashboard  ·  Sidebar status chips  ·  st.status() streaming panel  ·  Ishikawa card grid",
      8.5, color=C["muted"])

# ═══════════════════════════════════════════════════════════════════
# LAYER 2 — AGENT ENGINE  (middle)
# ═══════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 4.5, 17.2, 5.85, C["agent"], C["agent_bdr"],
           "AGENT LAYER  (agent.py  ·  LangGraph state machine)", C["agent_bdr"])

# NoruhAgent wrapper
box(ax, 0.75, 4.75, 16.5, 5.3, "#faf5ff", C["agent_bdr"], lw=1, radius=0.2)
label(ax, 9, 9.73, "NoruhAgent", 9, "bold", C["agent_bdr"])

# ── 4 graph nodes ────────────────────────────────────────────────
NODE_Y   = 8.25
NODE_H   = 1.15
NODE_W   = 3.2
GAPS     = [1.05, 4.55, 8.05, 11.55]
TITLES   = ["tool_caller", "tool_executor", "critic", "ishikawa_formatter"]
SUBTITLES= ["qwen3-coder:7b\n(via Ollama)", "Runs tools\nagainst DB",
            "deepseek-r1:8b\n(via Ollama)", "Builds\nIshikawaAnalysis"]

for i, (gx, t, s) in enumerate(zip(GAPS, TITLES, SUBTITLES)):
    box(ax, gx, NODE_Y, NODE_W, NODE_H, C["node"], C["node_bdr"], lw=2)
    label(ax, gx + NODE_W/2, NODE_Y + 0.82, t, 9.5, "bold", C["agent_bdr"])
    label(ax, gx + NODE_W/2, NODE_Y + 0.42, s, 8, color=C["muted"])

# arrows between nodes (→)
for i in range(3):
    x1 = GAPS[i] + NODE_W
    x2 = GAPS[i+1]
    mx = (x1 + x2) / 2
    my = NODE_Y + NODE_H / 2
    arrow(ax, x1, my, x2, my, C["node_bdr"], lw=2)

# retry loop: critic → tool_caller (curved back arrow below nodes)
ax.annotate("", xy=(GAPS[0] + NODE_W/2, NODE_Y),
            xytext=(GAPS[2] + NODE_W/2, NODE_Y),
            arrowprops=dict(arrowstyle="->", color="#dc2626", lw=1.5,
                            connectionstyle="arc3,rad=0.35"), zorder=4)
ax.text(6.5, 7.55, "INSUFFICIENT (retry, max 3×)", fontsize=7.5,
        color="#dc2626", ha="center", style="italic")

# SUFFICIENT label
ax.text(13.6, NODE_Y + NODE_H/2 + 0.12, "SUFFICIENT →", fontsize=7.5,
        color="#16a34a", ha="center", fontweight="bold")

# ── AgentState box ───────────────────────────────────────────────
box(ax, 1.0, 5.05, 5.5, 2.85, "#fdf4ff", "#c084fc", lw=1.2, radius=0.15)
label(ax, 3.75, 7.58, "AgentState", 9, "bold", "#7c3aed")
items = [
  "messages  (conversation history)",
  "tool_results  (SQL + search outputs)",
  "retry_count  (0 → 3)",
  "ishikawa  (final structured output)",
]
for j, it in enumerate(items):
    label(ax, 3.75, 7.25 - j*0.47, f"• {it}", 7.8, color=C["muted"])

# ── Tools box ───────────────────────────────────────────────────
box(ax, 7.2, 5.05, 4.6, 2.85, "#fdf4ff", "#c084fc", lw=1.2, radius=0.15)
label(ax, 9.5, 7.58, "Tools  (database.py)", 9, "bold", "#7c3aed")
label(ax, 9.5, 7.18, "execute_sql(sql)", 8.5, color=C["text"])
label(ax, 9.5, 6.88, "→ read-only DuckDB query", 7.8, color=C["muted"])
label(ax, 9.5, 6.5,  "semantic_search(query)", 8.5, color=C["text"])
label(ax, 9.5, 6.2,  "→ ChromaDB cosine similarity", 7.8, color=C["muted"])
label(ax, 9.5, 5.82, "SQL guard: sqlglot AST + regex", 7.5, color="#dc2626")

# ── IshikawaAnalysis schema box ──────────────────────────────────
box(ax, 12.5, 5.05, 4.6, 2.85, "#fdf4ff", "#c084fc", lw=1.2, radius=0.15)
label(ax, 14.8, 7.58, "IshikawaAnalysis  (Pydantic)", 9, "bold", "#7c3aed")
for j, f in enumerate(["machine  [ ]", "material  [ ]", "method  [ ]",
                        "human_environment  [ ]", "summary  str",
                        "anomalies_found  [ ]"]):
    label(ax, 14.8, 7.22 - j*0.39, f"• {f}", 7.5, color=C["muted"])

# ═══════════════════════════════════════════════════════════════════
# LAYER 3 — OLLAMA  (bottom-left)
# ═══════════════════════════════════════════════════════════════════
section_bg(ax, 0.4, 0.45, 8.2, 3.75, C["ollama"], C["ollama_bdr"],
           "OLLAMA  (local LLM server · localhost:11434)", C["ollama_bdr"])

# qwen3-coder
box(ax, 0.75, 0.72, 3.5, 2.8, C["model"], C["model_bdr"], lw=1.8)
label(ax, 2.5, 3.12, "qwen3-coder:7b", 10, "bold", "#92400e")
label(ax, 2.5, 2.72, "Tool-Calling Engine", 8.5, color=C["muted"])
label(ax, 2.5, 2.42, "• Writes DuckDB SQL", 8, color=C["text"])
label(ax, 2.5, 2.14, "• Issues tool calls", 8, color=C["text"])
label(ax, 2.5, 1.86, "• Writes <ishikawa> JSON", 8, color=C["text"])
label(ax, 2.5, 1.55, "~4.7 GB  ·  keep_alive=0", 7.5, color=C["muted"], weight="normal")

# deepseek-r1
box(ax, 4.75, 0.72, 3.5, 2.8, C["model"], C["model_bdr"], lw=1.8)
label(ax, 6.5, 3.12, "deepseek-r1:8b", 10, "bold", "#92400e")
label(ax, 6.5, 2.72, "Critic / Reasoning Engine", 8.5, color=C["muted"])
label(ax, 6.5, 2.42, "• Reads <think> blocks", 8, color=C["text"])
label(ax, 6.5, 2.14, "• Issues SUFFICIENT /", 8, color=C["text"])
label(ax, 6.5, 1.86, "  INSUFFICIENT verdict", 8, color=C["text"])
label(ax, 6.5, 1.55, "~4.9 GB  ·  keep_alive=0", 7.5, color=C["muted"])

# ═══════════════════════════════════════════════════════════════════
# LAYER 3 — DATA  (bottom-right)
# ═══════════════════════════════════════════════════════════════════
section_bg(ax, 9.0, 0.45, 8.6, 3.75, C["data"], C["data_bdr"],
           "DATA LAYER  (database.py  ·  NoruhDB)", C["data_bdr"])

# DuckDB
box(ax, 9.35, 0.72, 3.8, 2.8, C["db"], C["db_bdr"], lw=1.8)
label(ax, 11.25, 3.12, "DuckDB", 10, "bold", "#166534")
label(ax, 11.25, 2.75, "noruh_quality.db  (~92 MB)", 8, color=C["muted"])
for j, t in enumerate(["cnc_telemetry  (~657k rows)",
                        "lab_testing  (~655k rows)",
                        "packaging_log  (~218k rows)",
                        "customer_feedback  (10,838)"]):
    label(ax, 11.25, 2.38 - j*0.42, f"• {t}", 7.8, color=C["text"])
label(ax, 11.25, 0.95, "5 injected anomalies · 5-year history", 7.5, color=C["muted"])

# ChromaDB
box(ax, 13.55, 0.72, 3.6, 2.8, C["db"], C["db_bdr"], lw=1.8)
label(ax, 15.35, 3.12, "ChromaDB", 10, "bold", "#166534")
label(ax, 15.35, 2.75, "Vector Store  (chroma_db/)", 8, color=C["muted"])
label(ax, 15.35, 2.38, "• 10,838 feedback docs", 7.8, color=C["text"])
label(ax, 15.35, 2.0,  "• BAAI/bge-small-en-v1.5", 7.8, color=C["text"])
label(ax, 15.35, 1.62, "  (TF-IDF fallback offline)", 7.5, color=C["muted"])
label(ax, 15.35, 1.24, "• Cosine similarity search", 7.8, color=C["text"])
label(ax, 15.35, 0.86, "• Persistent on disk", 7.8, color=C["text"])

# ═══════════════════════════════════════════════════════════════════
# INTER-LAYER ARROWS
# ═══════════════════════════════════════════════════════════════════

# User → Streamlit (question)
arrow(ax, 9, 10.6, 9, 10.05, C["ui_bdr"], lw=2)

# Streamlit → Agent
arrow(ax, 9, 10.6, 9, 10.1, C["ui_bdr"], lw=2)
arrow(ax, 9, 10.6, 9, 10.1, C["ui_bdr"], lw=2)

# app.py ↔ NoruhAgent
arrow(ax, 7.5, 10.6, 4.5, 10.1, C["ui_bdr"], lw=1.5)
ax.annotate("", xy=(7.5, 10.6), xytext=(9, 10.6),
            arrowprops=dict(arrowstyle="<-", color=C["ui_bdr"], lw=1.5), zorder=4)

# tool_executor → Ollama (tool calls)
arrow(ax, 6.15, 8.25, 4.0, 4.52, C["ollama_bdr"], lw=1.5)

# tool_executor → DuckDB
arrow(ax, 7.5, 8.25, 11.25, 4.22, C["data_bdr"], lw=1.5)

# tool_executor → ChromaDB
arrow(ax, 8.0, 8.25, 15.35, 4.22, C["data_bdr"], lw=1.5)

# tool_caller → Ollama
arrow(ax, 2.65, 8.25, 2.5, 3.52, C["ollama_bdr"], lw=1.5)

# critic → Ollama
arrow(ax, 9.65, 8.25, 6.5, 3.52, C["ollama_bdr"], lw=1.5)

# ishikawa_formatter → app.py
arrow(ax, 14.15, 9.4, 12, 10.72, C["agent_bdr"], lw=1.5)

# ═══════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════
legend_items = [
    mpatches.Patch(facecolor=C["ui"],     edgecolor=C["ui_bdr"],     label="UI Layer"),
    mpatches.Patch(facecolor=C["agent"],  edgecolor=C["agent_bdr"],  label="Agent Layer"),
    mpatches.Patch(facecolor=C["ollama"], edgecolor=C["ollama_bdr"], label="Ollama / Models"),
    mpatches.Patch(facecolor=C["data"],   edgecolor=C["data_bdr"],   label="Data Layer"),
]
ax.legend(handles=legend_items, loc="lower right",
          bbox_to_anchor=(1.0, 0.0), framealpha=0.9, fontsize=8.5)

plt.tight_layout(pad=0.3)
plt.savefig("noruh_architecture.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("Saved noruh_architecture.png")
