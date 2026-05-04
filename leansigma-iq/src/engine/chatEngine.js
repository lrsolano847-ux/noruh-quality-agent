export const PHASES = {
  DEFINE:   { id: "define",   label: "Define",   color: "#6366f1", minScore: 1 },
  MEASURE:  { id: "measure",  label: "Measure",  color: "#8b5cf6", minScore: 4 },
  ANALYZE:  { id: "analyze",  label: "Analyze",  color: "#f59e0b", minScore: 6 },
  IMPROVE:  { id: "improve",  label: "Improve",  color: "#10b981", minScore: 8 },
  CONTROL:  { id: "control",  label: "Control",  color: "#06b6d4", minScore: 9 },
};

export const METHODOLOGY = {
  LEAN: "LEAN",
  SIX_SIGMA: "SIX_SIGMA",
  HYBRID: "HYBRID",
};

export function detectMethodology(text) {
  const t = text.toLowerCase();
  const leanTriggers    = ["slow", "clutter", "wait", "delay", "backlog", "inventory", "waste", "flow"];
  const sigmaTriggers   = ["error", "defect", "inconsisten", "variation", "quality", "reject", "scrap"];
  const hasLean  = leanTriggers.some(k => t.includes(k));
  const hasSigma = sigmaTriggers.some(k => t.includes(k));
  if (hasLean && hasSigma) return METHODOLOGY.HYBRID;
  if (hasSigma) return METHODOLOGY.SIX_SIGMA;
  if (hasLean)  return METHODOLOGY.LEAN;
  return null;
}

export function getPhaseForScore(score) {
  if (score >= 9) return PHASES.CONTROL;
  if (score >= 8) return PHASES.IMPROVE;
  if (score >= 6) return PHASES.ANALYZE;
  if (score >= 4) return PHASES.MEASURE;
  return PHASES.DEFINE;
}

export const DEMO_STEPS = [
  {
    id: 0,
    userMsg: "Our production line has a 14-day cycle time and we're seeing a lot of defects. We need to fix this fast.",
    scoreAfter: 3,
    methodology: METHODOLOGY.HYBRID,
    thinking: [
      "Detecting keywords: 'cycle time' → Lean trigger, 'defects' → Six Sigma trigger",
      "Routing: HYBRID methodology selected — 'Simplify before Stabilize' protocol active",
      "Score assessment: Symptom-level only. Missing quantified baselines.",
      "Current info score: 3/10 — DIAGNOSTIC state. Socratic mode engaged.",
    ],
    agentMsg: `**[HYBRID PROTOCOL ACTIVATED]** I've detected both flow and quality symptoms. Before prescribing any solution, I need to establish a rigorous baseline.

**Current Info Score: 3/10 — DIAGNOSTIC**

⚠️ **Stop-Gate: ACTIVE.** I cannot recommend improvements until we validate data.

I have two diagnostic questions to calibrate this project:

1. **Flow dimension:** What is your current Total Lead Time vs. Total Cycle Time? (This distinguishes waiting waste from process waste.)
2. **Quality dimension:** What is your current defect rate (DPMO or %) and do you have a stratified breakdown by defect type?

Per the "Simplify before Stabilize" mandate — we will address Lean waste first, then apply Six Sigma to reduce variation. Jumping to solutions now would accelerate a broken process.

👉 **Next Action:** Upload your process step data to the Data Canvas to begin the VSM diagnostic.`,
    quickReplies: ["Upload process data", "I don't have data yet", "What data do I need?"],
    activeTools: ["VSM Diagnostic", "Defect Stratification"],
    unlockedPanel: null,
  },
  {
    id: 1,
    userMsg: "I've uploaded our process step data. We have 7 steps: Receiving through Shipping.",
    scoreAfter: 5,
    methodology: METHODOLOGY.HYBRID,
    thinking: [
      "Data received: 7 process steps with C/T, C/O, Uptime, WIP counts",
      "SCANNING for Hidden Factory indicators...",
      "⚠️ ALERT: Repeated Work Order IDs detected — 'Rework Loop' confirmed",
      "WO-1042 appears 3x, WO-1087 appears 2x, WO-1156 appears 2x",
      "Hidden Factory Logic triggered: Lean VSM must pause. Six Sigma root cause required.",
      "Score updated: 5/10 — GAP ANALYSIS state.",
    ],
    agentMsg: `**Data received. Running Gap Analysis...**

**Current Info Score: 5/10 — GAP ANALYSIS**

📊 **VSM Preliminary Results:**
- Total Lead Time: ~14.2 days
- Total Value-Added Time: 3.2 hours (1.6% efficiency)
- Largest WIP queue: **Machining A — 203 units**

🚨 **HIDDEN FACTORY DETECTED**

While scanning your data, I identified **repeated Work Order IDs** (WO-1042 ×3, WO-1087 ×2, WO-1156 ×2). This confirms an undocumented rework loop consuming ~38 sec/unit with 65% uptime.

**[METHODOLOGY PIVOT REQUIRED]**

> "What appears to be a Lean flow problem is actually a Six Sigma quality problem hiding inside the process."

**Stop-Gate: ACTIVE** — I am pausing the VSM workflow. Before optimizing flow speed, we must eliminate the defect source driving these rework loops.

**Missing data to reach Score 8:**
- [ ] Defect stratification by type (Pareto)
- [ ] Process stability data (25 subgroups for SPC)
- [ ] Measurement system validation (Gage R&R)

👉 **Field Assignment dispatched:** Defect Stratification Check Sheet`,
    quickReplies: ["Load defect data", "Show me the Pareto", "What is Gage R&R?"],
    activeTools: ["Hidden Factory Scan", "Defect Stratification", "Gap Analysis"],
    unlockedPanel: "pareto",
  },
  {
    id: 2,
    userMsg: "Here is our defect frequency data by type. Dimensional errors are the top issue.",
    scoreAfter: 7,
    methodology: METHODOLOGY.SIX_SIGMA,
    thinking: [
      "Defect data loaded. Running Pareto analysis...",
      "Dimensional Error: 148 occurrences (39.6% of total)",
      "Top 2 defect types (Dimensional + Surface Finish) = 65.5% of all defects",
      "Pareto principle validated: vital few identified",
      "SPC prerequisite check: Need 25 subgroups for control chart",
      "FMEA prerequisite: RPN scores must be calculated before improvement actions",
      "Score updated: 7/10 — approaching Solution Mode threshold",
    ],
    agentMsg: `**Pareto Analysis Complete.**

**Current Info Score: 7/10 — GAP ANALYSIS (Critical)**

📊 **Vital Few Identified:**
- **Dimensional Error:** 148 units (39.6%) ← Primary target
- **Surface Finish:** 97 units (26.0%)
- Combined: **65.5% of all defects** from 2 causes

This validates the Pareto Principle. Resources must be concentrated on Dimensional Error root cause.

**⚠️ Stop-Gate: STILL ACTIVE**

Before I can unlock the Improvement Roadmap, I require:

1. **Process Stability (SPC):** The control chart shows **2 Special Cause violations** at subgroups 12 and 19. A process is not predictable if it is not stable — I cannot calculate Cpk until these are explained.

2. **FMEA:** Risk Priority Numbers must be calculated. Preliminary scan shows **Final QC inspector drift has RPN 486** — a Poka-Yoke solution is **mandatory** before proceeding to Control.

👉 **Load the stability data to reach Score 8 and unlock the Improvement Roadmap.**`,
    quickReplies: ["Load stability data + FMEA", "Explain Special Cause violations", "Show FMEA table"],
    activeTools: ["Pareto Chart", "SPC Control Chart", "FMEA Risk Table"],
    unlockedPanel: "controlchart",
  },
  {
    id: 3,
    userMsg: "Here is the SPC data — 25 subgroups collected. Also attaching our FMEA.",
    scoreAfter: 8,
    methodology: METHODOLOGY.SIX_SIGMA,
    thinking: [
      "SPC data: 25 subgroups received. Calculating UCL/LCL...",
      "UCL = 58.4, LCL = 35.6, CL = 47.0",
      "Special Cause violations confirmed: subgroups 12 and 19 exceed UCL",
      "Root cause hypothesis: Tool wear at Machining A (RPN 378) + no TPM schedule",
      "FMEA loaded. Highest RPN: Final QC inspector drift = 486 (S=9, O=6, D=9)",
      "Cpk cannot be calculated until special causes are eliminated",
      "All Stop-Gate conditions satisfied. Unlocking Solution Mode.",
      "INFO SCORE: 8/10 — SOLUTION MODE UNLOCKED",
    ],
    agentMsg: `**All Stop-Gate conditions satisfied.**

# 🔓 INFO SCORE: 8/10 — IMPROVEMENT ROADMAP UNLOCKED

The data is now statistically sufficient. Here is your prioritized improvement plan.

---

## Phase 1 — Stabilize (Six Sigma)
**Priority 1: Eliminate Special Cause at Machining A**
- Root cause: No Preventive Maintenance (TPM) schedule → progressive tool wear
- Action: Implement statistical tool-change trigger at Cp degradation threshold
- Expected impact: Eliminate 2 control chart violations → process in-control

**Priority 2: Mandatory Poka-Yoke (RPN 486)**
- Final QC inspector drift cannot be addressed by manual re-inspection
- Action: Install automated vision system or go/no-go fixture
- Regulatory note: You **cannot proceed to Control phase** with manual inspection on Severity-9 failures

---

## Phase 2 — Simplify (Lean)
Once the process is in statistical control:
- **Machining A WIP reduction:** Pull-based scheduling (Kanban eligible after lead time stabilizes)
- **VSM Future State:** Target 65% reduction in Total Lead Time
- **Takt Time recalculation** based on corrected cycle times post-rework elimination

---

## Sigma Level Projection
| Metric | Current | Target |
|--------|---------|--------|
| DPMO | ~41,200 | <6,800 |
| Sigma Level | 3.2σ | >4.0σ |
| Cpk | ~0.87 | >1.33 |`,
    quickReplies: ["Generate PDF Work Order", "Show Kanban calculation", "View full FMEA"],
    activeTools: ["Improvement Roadmap", "Cpk Calculator", "Kanban Designer", "Poka-Yoke Audit"],
    unlockedPanel: "roadmap",
  },
];

export const FALLBACK_RESPONSES = {
  lean: {
    thinking: ["Lean trigger detected: flow/waste keywords", "Routing to VSM + 5S diagnostic", "Checking for standardized baseline..."],
    msg: `**Lean Workflow Initiated**\n\nI've detected flow-related symptoms. Before any improvement:\n\n⚠️ **Stop-Gate:** We cannot optimize a process that isn't standardized.\n\n**Required:** Document the current work sequence for 3 different operators (Standard Work Sheet). Upload VSM data to the Data Canvas to begin.\n\n*Info Score too low to prescribe solutions.*`,
  },
  sixsigma: {
    thinking: ["Six Sigma trigger detected: defects/variation keywords", "Routing to SPC + Gage R&R diagnostic", "Checking measurement system validity..."],
    msg: `**Six Sigma Workflow Initiated**\n\nQuality variation symptoms detected.\n\n⚠️ **Stop-Gate:** We cannot identify root causes without validated measurement data.\n\n**Required:**\n1. Gage R&R study (3 operators × 10 parts × 2 trials)\n2. 25-subgroup stability baseline\n\n*Proceeding to Analyze phase without these will produce dishonest statistics.*`,
  },
  default: {
    thinking: ["Keyword analysis: insufficient domain signals", "Entering Socratic diagnostic mode", "Requesting problem framing from user"],
    msg: `I need more specificity to route this correctly.\n\nCould you describe the problem in terms of:\n- **Speed/Flow:** Is the process slow, backed up, or cluttered?\n- **Quality:** Are there errors, defects, or inconsistent outputs?\n- **Both?**\n\nThis determines whether we deploy Lean, Six Sigma, or a Hybrid approach. What does your data show?`,
  },
};
