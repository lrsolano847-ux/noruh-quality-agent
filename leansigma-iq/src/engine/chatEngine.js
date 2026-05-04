export const PHASES = {
  DEFINE:  { id: "define",  label: "Define",  color: "#6366f1", scoreRange: "1-4" },
  MEASURE: { id: "measure", label: "Measure", color: "#8b5cf6", scoreRange: "4-5" },
  ANALYZE: { id: "analyze", label: "Analyze", color: "#f59e0b", scoreRange: "6-7" },
  IMPROVE: { id: "improve", label: "Improve", color: "#10b981", scoreRange: "8-9" },
  CONTROL: { id: "control", label: "Control", color: "#06b6d4", scoreRange: "10" },
};

export const METHODOLOGY = { LEAN: "LEAN", SIX_SIGMA: "SIX_SIGMA", HYBRID: "HYBRID" };

export function detectMethodology(text) {
  const t = text.toLowerCase();
  const lean  = ["slow","clutter","wait","delay","backlog","inventory","waste","flow","lead time","cycle time"];
  const sigma = ["error","defect","inconsisten","variation","quality","reject","scrap","defect","rework"];
  const hasLean  = lean.some(k => t.includes(k));
  const hasSigma = sigma.some(k => t.includes(k));
  if (hasLean && hasSigma) return METHODOLOGY.HYBRID;
  if (hasSigma) return METHODOLOGY.SIX_SIGMA;
  if (hasLean)  return METHODOLOGY.LEAN;
  return null;
}

export function getPhaseForScore(score) {
  if (score >= 10) return PHASES.CONTROL;
  if (score >= 8)  return PHASES.IMPROVE;
  if (score >= 6)  return PHASES.ANALYZE;
  if (score >= 4)  return PHASES.MEASURE;
  return PHASES.DEFINE;
}

export const DEMO_STEPS = [
  {
    id: 0,
    userMsg: "Our production line has a 14-day cycle time and we're seeing a lot of defects. We need to fix this fast.",
    scoreAfter: 3,
    methodology: METHODOLOGY.HYBRID,
    thinking: [
      "Scanning input for domain keywords...",
      "Lean triggers detected: 'cycle time', '14-day'",
      "Six Sigma triggers detected: 'defects'",
      "→ Routing: HYBRID methodology — 'Simplify before Stabilize' protocol activated",
      "Score assessment: symptom-level only, no quantified baseline",
      "current_info_score = 3 → DIAGNOSTIC state. Socratic mode engaged.",
      "Stop-Gate: ACTIVE — solution blocked until score ≥ 8",
    ],
    agentMsg: `**[HYBRID PROTOCOL ACTIVATED]**

Hiring more people or adding machines right now would just be paying to move waste faster. We need data before prescriptions.

**Current Info Score: 3/10 — DIAGNOSTIC (Define Phase)**

> ⛔ **Stop-Gate ACTIVE:** I am prohibited from issuing an Improvement Roadmap until your Info Score reaches 8/10.

I've detected two distinct problem signatures in your description:
- **Flow problem** → "14-day cycle time" signals a Lean / VSM diagnostic
- **Quality problem** → "a lot of defects" signals a Six Sigma / SPC diagnostic

Per the **"Simplify before Stabilize"** mandate, we address Lean waste first — then apply Six Sigma to variation. Jumping to solutions now risks accelerating a broken process.

**I need answers to two questions to calibrate this project:**

1. What is your **Total Lead Time vs. Total Cycle Time**? (Separates waiting waste from process waste.)
2. What is your **defect rate** and do you have a breakdown by defect type?

👉 **Field Assignment dispatched:** *Value Stream Diagnostic* — walk the process from Shipping back to Supplier and upload actual Gemba observations to the Data Canvas. Do not use ERP estimates.`,
    quickReplies: [
      "Upload process step data →",
      "I don't have cycle time data yet",
      "What's the difference between lead time and cycle time?",
    ],
    activeTools: ["VSM Diagnostic", "Defect Stratification"],
    unlockedPanel: "vsm",
  },
  {
    id: 1,
    userMsg: "I've uploaded our process step data — 7 steps from Receiving to Shipping with cycle times, uptime, and WIP counts.",
    scoreAfter: 5,
    methodology: METHODOLOGY.HYBRID,
    thinking: [
      "Data received: 7 process steps — C/T, C/O, Uptime, WIP",
      "Calculating Total Lead Time...",
      "Calculating VA Ratio = Total VA Time / Total Lead Time × 100",
      "VA Ratio = (3.2 hrs / 14.2 days) = 1.6% — severe NVA ratio",
      "Largest WIP queue: Machining A = 203 units → primary bottleneck",
      "⚠️ SCANNING for Hidden Factory indicators...",
      "Repeated Work Order IDs detected: WO-1042 ×3, WO-1087 ×2, WO-1156 ×2",
      "→ Hidden Factory: undocumented rework loop confirmed at 65% uptime",
      "PIVOT REQUIRED: Lean VSM paused. Six Sigma root cause mandatory.",
      "current_info_score = 5 → GAP ANALYSIS state",
    ],
    agentMsg: `**Data received. Running VSM Gap Analysis...**

**Current Info Score: 5/10 — GAP ANALYSIS (Measure Phase)**

---

### VSM Preliminary Results

| Metric | Value |
|--------|-------|
| Total Lead Time | **14.2 days** |
| Total VA Time | 3.2 hours |
| **VA Ratio** | **1.6%** ← 98.4% is waste |
| Largest WIP Queue | Machining A — 203 units |

---

### 🚨 HIDDEN FACTORY DETECTED

While scanning your Work Order IDs, I found repeated entries:
**WO-1042 ×3 · WO-1087 ×2 · WO-1156 ×2**

This confirms an **undocumented rework loop** — parts cycling back through the process and consuming resources without appearing in your yield figures. This is the classic "Foundry Problem": your First-Pass Yield looks acceptable, but the Rolled Throughput Yield (RTY = ∏FPYᵢ) reveals the true cost.

### ⛔ METHODOLOGY PIVOT REQUIRED

> "What appears to be a Lean flow problem is actually a Six Sigma quality problem hiding inside the process."

I am **pausing the VSM workflow**. Optimizing flow speed before eliminating the defect source would only accelerate the rework loop.

**Gaps remaining before Score 8:**
- [ ] Defect stratification by type (Pareto Analysis)
- [ ] 25-subgroup stability baseline (SPC / Control Chart)
- [ ] Measurement system validation (Gage R&R)

👉 **Field Assignment dispatched:** *Defect Stratification Check Sheet* — record defect type and frequency for one full production shift.`,
    quickReplies: [
      "Load defect frequency data →",
      "Explain the Hidden Factory concept",
      "Show me the RTY calculation",
    ],
    activeTools: ["Hidden Factory Scan", "VSM Analysis", "Gap Analysis"],
    unlockedPanel: "pareto",
  },
  {
    id: 2,
    userMsg: "Here is our defect data by type. Dimensional errors are by far the biggest category.",
    scoreAfter: 7,
    methodology: METHODOLOGY.SIX_SIGMA,
    thinking: [
      "Defect data received. Running Pareto analysis...",
      "Total defects: 380",
      "Dimensional Error: 148 (38.9%) ← vital few, primary target",
      "Surface Finish: 97 (25.5%)",
      "Top 2 types = 64.5% of all defects — Pareto principle confirmed",
      "Routing: Six Sigma — SPC + FMEA required",
      "SPC prerequisite: need 25 subgroups for control limits",
      "FMEA check: RPN calculations mandatory before any improvement action",
      "current_info_score = 7 → approaching Solution Mode threshold",
      "Stop-Gate: STILL ACTIVE — 1 point from unlock",
    ],
    agentMsg: `**Pareto Analysis Complete.**

**Current Info Score: 7/10 — GAP ANALYSIS (Analyze Phase)**

---

### Vital Few Identified

| Defect Type | Count | % of Total | Cumulative % |
|-------------|-------|------------|--------------|
| Dimensional Error | 148 | 38.9% | 38.9% |
| Surface Finish | 97 | 25.5% | 64.5% ← |
| Misalignment | 74 | 19.5% | 83.9% |
| Missing Component | 31 | 8.2% | 92.1% |
| Other | 30 | 7.9% | 100% |

The "vital few" are confirmed. **Two defect types drive 64.5% of all failures.** Resources must concentrate on Dimensional Error root cause — likely the Machining A bottleneck with 71% uptime.

---

### ⛔ Stop-Gate: STILL ACTIVE — two conditions unmet

**1. Process Stability (SPC):** I need 25 subgroups from Machining A *without process adjustment* during collection. The control chart preview shows **2 suspected Special Cause violations** — a process not in statistical control cannot have its capability (Cpk) calculated.

**2. FMEA:** Risk Priority Numbers must be established before any improvement action. Preliminary scan flags:
- Final QC Inspector Drift → estimated **RPN ~486** (S=9, O=6, D=9)
- A Poka-Yoke solution is **mandatory** for any Severity ≥ 8 item

👉 **Upload the 25-subgroup stability data + FMEA to reach Score 8.**`,
    quickReplies: [
      "Load SPC data + FMEA →",
      "What is Cpk and why does stability matter first?",
      "Explain the RPN 486 risk",
    ],
    activeTools: ["Pareto Chart", "SPC Preview", "FMEA Table", "Gap Analysis"],
    unlockedPanel: "controlchart",
  },
  {
    id: 3,
    userMsg: "Uploading 25-subgroup SPC data and our completed FMEA now.",
    scoreAfter: 8,
    methodology: METHODOLOGY.SIX_SIGMA,
    thinking: [
      "SPC data: 25 subgroups received.",
      "Calculating control limits: UCL = 58.4, LCL = 35.6, CL = 47.0",
      "Violation check: subgroup 12 = 61.2 (above UCL) ✗",
      "Violation check: subgroup 19 = 63.8 (above UCL) ✗",
      "Special cause hypothesis: progressive tool wear at Machining A",
      "FMEA loaded. Highest RPN: Final QC inspector drift = 486 (S=9, O=6, D=9)",
      "Poka-Yoke mandatory: Severity 9 cannot proceed to Control with manual inspection",
      "Cpk prerequisite check: special causes must be eliminated before Cpk is valid",
      "All Stop-Gate conditions now satisfied.",
      "→ current_info_score = 8 — SOLUTION MODE UNLOCKED 🔓",
    ],
    agentMsg: `**All Stop-Gate conditions satisfied. Unlocking Solution Mode.**

---

# 🔓 INFO SCORE: 8/10 — IMPROVEMENT ROADMAP UNLOCKED

The data is statistically sufficient. Here is your prioritized, evidence-based improvement plan.

---

## Phase 1 — Stabilize First (Six Sigma)

**Priority 1: Eliminate Special Cause at Machining A** *(RPN 378)*
- Root cause: No TPM schedule → progressive tool wear
- Evidence: Subgroups 12 and 19 exceed UCL (tool not changed on schedule)
- Action: Implement statistical tool-change trigger at Cp degradation threshold
- Expected outcome: Process returns to statistical control → Cpk calculable

**Priority 2: Mandatory Poka-Yoke** *(RPN 486 — highest risk)*
- Final QC inspector drift **cannot** be resolved by adding inspectors
- Action: Install automated vision system or precision go/no-go fixture
- ⚠️ Regulatory note: You **cannot advance to the Control phase** with a Severity-9 failure relying on manual detection

---

## Phase 2 — Simplify Flow (Lean)

Once the process is in statistical control:
- **Kanban design** for Machining A (stable lead time is prerequisite — currently σ=2.1 days, must reduce)
- **VSM Future State:** Target 65% reduction in Total Lead Time via WIP caps
- **Takt Time recalculation** after rework loop is eliminated

---

## Sigma Level Projection

| Metric | Current | Target |
|--------|---------|--------|
| DPMO | ~41,200 | < 6,800 |
| Sigma Level | 3.2σ | ≥ 4.0σ |
| Cpk (est.) | ~0.87 | ≥ 1.33 |
| RTY | ~61% | ≥ 85% |`,
    quickReplies: [
      "Generate PDF Work Order for Machining A",
      "Calculate Kanban bins for Assembly",
      "Show full FMEA with RPN priorities",
    ],
    activeTools: ["Improvement Roadmap", "Cpk Calculator", "Kanban Designer", "Poka-Yoke Audit"],
    unlockedPanel: "roadmap",
  },
];

export const FAILURE_SCENARIOS = [
  {
    id: "hidden-factory",
    label: "Hidden Factory Case",
    userMsg: "A foundry reported high First-Pass Yields, but operational costs were double the theoretical calculations. Sigma level was 2.33. Why?",
    thinking: [
      "Failure analysis mode — examining RTY vs FPY discrepancy",
      "Cost variance: 2× theoretical → undocumented labor/material consumption",
      "Sigma 2.33 → DPMO ≈ 100,000 (far worse than FPY suggests)",
      "Hypothesis: Hidden Factory — rework loops excluded from formal tracking",
      "RTY = ∏FPYᵢ reveals true yield across all steps",
    ],
    agentMsg: `**Failure Analysis: The Hidden Factory**

This is a hallmark failure of ignoring the **Rolled Throughput Yield (RTY)**.

**The Pathology:** Flawed castings were returned to earlier stages for grinding/welding *without documentation*. Management tracked final shipments (First-Pass Yield) but never measured yield at each step. Because RTY = ∏FPYᵢ, even 95% yield at each of 6 steps produces:

> RTY = 0.95⁶ = **0.735 — a true yield of only 73.5%**

The remaining 26.5% was being reworked invisibly, consuming 30% more energy and labor than the output justified.

**Warning Signs That Were Missed:**
- Informal "rework piles" near workstations excluded from the VSM
- Capacity discrepancy: plant consumed 30% more energy than output volume predicted
- Operators performing unrecorded corrections between shifts`,
  },
  {
    id: "wrong-tool",
    label: "Tool Mismatch Case",
    userMsg: "A chemical lab ran a 5S and VSM project to fix diagnostic report delays. Workspace was cleaner but lead times didn't improve. Why did it fail?",
    thinking: [
      "Failure analysis: Lean tools applied to a variation problem",
      "5S, VSM = flow/waste tools — cannot address statistical variation",
      "Lab delays → likely driven by retest rates, not physical layout",
      "Tool mismatch: Six Sigma (Gage R&R, DOE) required, not Lean",
      "Clean Lab Paradox: high organization score, no lead time improvement",
    ],
    agentMsg: `**Failure Analysis: The Tool Mismatch**

This failure is a classic case of **Incorrect Tool Selection** — applying Lean methodology to a Six Sigma variation problem.

**The Pathology:** The delays were driven by a **5% retest rate** caused by reagent inconsistency and equipment calibration drift. These are issues of *process variation*, not physical flow. Lean tools (5S, VSM) have no statistical mechanism to identify interaction effects between "Material" and "Measurement" variables.

**The Clean Lab Paradox:** The facility achieved high marks for organization. Workstations were immaculate. Yet lead times remained exactly the same — because the root cause was never touched.

**What Was Actually Needed:**
- **Gage R&R** to expose measurement system drift
- **DOE** to identify reagent/equipment interaction effects
- The "confirmatory retests" technicians were running informally needed to be *documented and analyzed*, not hidden

**LeanSigma IQ Stop-Gate this violated:** Applying only Lean tools to solve complex variation issues is the "speed of implementation trap" — you merely accelerate a broken process.`,
  },
  {
    id: "sampling-bias",
    label: "Sampling Bias Case",
    userMsg: "A bank redesigned staffing based on a two-week study of wait times. Friday complaints hit an all-time high after. What went wrong?",
    thinking: [
      "Failure analysis: insufficient sample size + temporal sampling bias",
      "Two-week study → missed Friday afternoon and month-end peaks",
      "Convenience sampling → dataset excluded high-volume periods",
      "Reported avg: 7.8 min. True 95th percentile on Fridays: 18.5 min",
      "Non-normal distribution: outliers were excluded rather than analyzed",
    ],
    agentMsg: `**Failure Analysis: Temporal Sampling Bias**

The project suffered from **Insufficient Sample Size** and **Convenience Sampling** — a critical Measure Phase failure.

**The Pathology:** Data was collected only on weekday mornings, missing:
- Friday afternoon volume surges
- Month-end transaction peaks
- Seasonal patterns

The Measure Phase produced an average wait time of **7.8 minutes**, but the true **95th percentile on Fridays was 18.5 minutes**. The staffing model was optimized for normal days — not the days customers actually complain about.

**Warning Signs That Were Missed:**
- Suspiciously low standard deviation in the dataset (a uniform distribution is a red flag in service processes)
- "Slow days" excluded as outliers rather than recognized as symptoms of a non-normal, bimodal distribution

**LeanSigma IQ would have blocked this:** The SPC Stop-Gate requires **25 subgroups collected without filtering** — including Fridays, month-ends, and peak periods. A Gage R&R on the timekeeping method would also have been required before advancing to Analyze.`,
  },
];

export const QUICK_TOOL_RESPONSES = {
  kanban: {
    thinking: ["Kanban calculation triggered", "Retrieving lead time stability metrics...", "Lead time σ=2.1 days → HIGH VARIATION detected", "Stop-Gate: Kanban blocked until SPC stabilizes lead time"],
    msg: `**Kanban Design — Stop-Gate Check**\n\n⛔ **BLOCKED:** Lead time σ = 2.1 days (coefficient of variation > 30%).\n\nThe Kanban formula **K = (d × L + S) / C** requires a *stable* lead time. High variation causes a pull system to collapse into frequent stockouts.\n\n**Required first:** Reduce lead time variation via SPC before calculating Kanban bin count.\n\nOnce stable, your preliminary calculation will be:\n- d = 42 units/day · L = 3.8 days · S = 15% · C = 20 units\n- **K ≈ 11 bins** (pending stability confirmation)`,
  },
  smed: {
    thinking: ["SMED diagnostic triggered", "Changeover time data required", "Checking for video time-motion study..."],
    msg: `**SMED Analysis — Gap Analysis**\n\n⛔ **PAUSED:** The Analyze phase cannot initiate until a continuous video time-motion study is completed.\n\n**Required:** Record changeover from "Last Good Part" of Run A to "First Good Part" of Run B. Break into timestamped actions, categorize as Internal (machine stopped) or External (can run concurrently).\n\n**Target:** Reduce changeover to < 10 minutes by converting Internal → External tasks.\n\n*Field Assignment dispatched: SMED Time & Motion Study template.*`,
  },
};
