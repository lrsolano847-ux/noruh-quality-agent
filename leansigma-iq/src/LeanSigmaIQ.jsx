import { useState, useEffect, useRef, useCallback } from 'react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell, LineChart, Legend,
} from 'recharts';

// ─── DESIGN TOKENS ───────────────────────────────────────────
const C = {
  bg:       '#0f172a',
  surface:  '#1e293b',
  surface2: '#263248',
  border:   '#334155',
  text:     '#f1f5f9',
  muted:    '#94a3b8',
  blue:     '#3b82f6',
  blueLight:'#60a5fa',
  green:    '#10b981',
  amber:    '#f59e0b',
  red:      '#ef4444',
  purple:   '#a855f7',
};

const s = {
  pane: { background: C.surface, borderRight: `1px solid ${C.border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  card: { background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 8, padding: '10px 12px' },
  badge: (color) => ({ background: color + '22', border: `1px solid ${color}55`, color, borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700 }),
  btn: (color = C.blue) => ({ background: color, color: '#fff', border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer' }),
  outlineBtn: { background: 'transparent', color: C.muted, border: `1px solid ${C.border}`, borderRadius: 6, padding: '6px 12px', fontSize: 12, cursor: 'pointer' },
  stopGate: { background: '#ef444415', border: `1px solid #ef444455`, borderRadius: 8, padding: '10px 14px', margin: '8px 0' },
  unlocked: { background: '#10b98115', border: `1px solid #10b98155`, borderRadius: 8, padding: '10px 14px', margin: '8px 0' },
};

// ─── STATIC DATA ─────────────────────────────────────────────
const PROCESS_STEPS = [
  { step: 'Receiving',   ct: 12, co: 0,  uptime: 98, wip: 45,  rework: false },
  { step: 'Inspection',  ct: 28, co: 5,  uptime: 82, wip: 112, rework: false },
  { step: 'Machining A', ct: 47, co: 35, uptime: 71, wip: 203, rework: false, bottleneck: true },
  { step: 'Rework Loop', ct: 38, co: 10, uptime: 65, wip: 88,  rework: true },
  { step: 'Assembly',    ct: 62, co: 20, uptime: 78, wip: 156, rework: false },
  { step: 'Final QC',    ct: 19, co: 0,  uptime: 90, wip: 67,  rework: false },
  { step: 'Shipping',    ct: 8,  co: 0,  uptime: 99, wip: 21,  rework: false },
];

const DEFECT_DATA = [
  { type: 'Dimensional',    short: 'Dim.Error', count: 148, cum: 38.9 },
  { type: 'Surface Finish', short: 'Surface',   count: 97,  cum: 64.5 },
  { type: 'Misalignment',   short: 'Misalign',  count: 74,  cum: 83.9 },
  { type: 'Missing Part',   short: 'Missing',   count: 31,  cum: 92.1 },
  { type: 'Label Error',    short: 'Label',     count: 18,  cum: 96.8 },
  { type: 'Other',          short: 'Other',     count: 12,  cum: 100  },
];

const CONTROL_DATA = [
  {sg:1,mean:46.2},{sg:2,mean:48.1},{sg:3,mean:44.9},{sg:4,mean:47.5},{sg:5,mean:45.8},
  {sg:6,mean:49.2},{sg:7,mean:46.1},{sg:8,mean:48.7},{sg:9,mean:45.3},{sg:10,mean:47.9},
  {sg:11,mean:46.5},{sg:12,mean:61.2},{sg:13,mean:47.1},{sg:14,mean:48.4},{sg:15,mean:46.8},
  {sg:16,mean:47.3},{sg:17,mean:45.9},{sg:18,mean:63.8},{sg:19,mean:46.7},{sg:20,mean:48.2},
  {sg:21,mean:45.4},{sg:22,mean:47.6},{sg:23,mean:46.9},{sg:24,mean:48.0},{sg:25,mean:47.2},
].map(d => ({ ...d, ucl: 58.4, lcl: 35.6, cl: 47.0, special: d.mean > 58.4 }));

const FMEA_DATA = [
  { step:'Final QC',    mode:'Inspector Drift', effect:'Escape to field', s:9, o:6, d:9, rpn:486, cause:'No Gage R&R',     control:'None'         },
  { step:'Machining A', mode:'Tool Wear',        effect:'Dim. OOT',        s:9, o:7, d:6, rpn:378, cause:'No TPM schedule', control:'Manual gauge'  },
  { step:'Assembly',    mode:'Wrong Torque',     effect:'Field failure',   s:8, o:5, d:7, rpn:280, cause:'No poka-yoke',   control:'Visual check'  },
  { step:'Inspection',  mode:'Missed Defect',    effect:'Rework cost',     s:6, o:8, d:5, rpn:240, cause:'Fatigue/volume', control:'Re-inspect'    },
];

const PHASES = ['Define','Measure','Analyze','Improve','Control'];
const PHASE_SCORES = [1, 4, 6, 8, 10];
const PHASE_COLORS = [C.blue, C.purple, C.amber, C.green, '#06b6d4'];

function getPhase(score) {
  if (score >= 10) return 4;
  if (score >= 8)  return 3;
  if (score >= 6)  return 2;
  if (score >= 4)  return 1;
  return 0;
}

// ─── DEMO SCRIPT ─────────────────────────────────────────────
const DEMO_STEPS = [
  {
    user: "Our production line has a 14-day cycle time and we're seeing a lot of defects. We need to fix this fast.",
    score: 3,
    method: 'HYBRID',
    thinking: [
      'Scanning input for domain keywords...',
      'Lean triggers: "cycle time", "14-day" ✓',
      'Six Sigma triggers: "defects" ✓',
      '→ HYBRID methodology — "Simplify before Stabilize" activated',
      'Score: symptom-level only, no quantified baseline',
      'current_info_score = 3 → DIAGNOSTIC state',
      '⛔ Stop-Gate ACTIVE — solution blocked until score ≥ 8',
    ],
    panel: 'vsm',
    agent: [
      { type: 'stop', text: '⛔ STOP-GATE ACTIVE — Info Score 3/10. Improvement Roadmap locked.' },
      { type: 'text', text: '**[HYBRID PROTOCOL ACTIVATED]** Hiring more people now would just accelerate a broken process. We need data before prescriptions.' },
      { type: 'text', text: 'I detected two problem signatures:\n• **Flow** → "14-day cycle time" = Lean / VSM diagnostic\n• **Quality** → "defects" = Six Sigma / SPC diagnostic' },
      { type: 'text', text: 'Per "Simplify before Stabilize" — Lean waste first, then Six Sigma stabilization. Two questions to calibrate:\n1. Total Lead Time vs. Total Cycle Time?\n2. Defect rate and stratification by type?' },
      { type: 'assign', text: '📋 Field Assignment: Value Stream Diagnostic — walk process Shipping → Supplier. Upload actual Gemba observations. No ERP estimates.' },
    ],
    replies: ['Upload process step data →', "What data do I need?", "Explain Hybrid methodology"],
  },
  {
    user: "I've uploaded our process step data — 7 steps from Receiving to Shipping with cycle times, uptime, and WIP.",
    score: 5,
    method: 'HYBRID',
    thinking: [
      'VSM data received: 7 process steps',
      'Total Lead Time = 14.2 days | Total VA Time = 3.2 hrs',
      'VA Ratio = 3.2hrs / (14.2 × 8hrs) = 2.8% — severe waste',
      'Largest WIP: Machining A = 203 units → primary bottleneck',
      '⚠️ SCANNING for Hidden Factory indicators...',
      'Repeated Work Order IDs: WO-1042 ×3, WO-1087 ×2, WO-1156 ×2',
      '→ Undocumented rework loop confirmed at 65% uptime',
      'RTY = ∏FPYᵢ — true yield far below reported FPY',
      'PIVOT: Lean VSM paused. Six Sigma root cause required.',
      'current_info_score = 5 → GAP ANALYSIS state',
    ],
    panel: 'vsm',
    agent: [
      { type: 'text', text: '**VSM Preliminary Results:**\n• Total Lead Time: **14.2 days**\n• Total VA Time: 3.2 hours\n• **VA Ratio: 2.8%** — 97.2% is Non-Value-Added\n• Largest WIP: Machining A (203 units)' },
      { type: 'stop', text: '🚨 HIDDEN FACTORY DETECTED — Repeated WO IDs found: WO-1042 ×3, WO-1087 ×2. Undocumented rework loop at 65% uptime.' },
      { type: 'text', text: '**[METHODOLOGY PIVOT]** What appears to be a flow problem is a quality problem hiding inside the process. I am pausing the VSM.\n\nRTY = ∏FPYᵢ — your real throughput yield is far lower than your reported First-Pass Yield.' },
      { type: 'text', text: '**Gaps to Score 8:**\n☐ Defect stratification (Pareto)\n☐ 25-subgroup stability study (SPC)\n☐ Measurement system validation (Gage R&R)' },
      { type: 'assign', text: '📋 Field Assignment: Defect Stratification Check Sheet — tally defect type and frequency for one full production shift.' },
    ],
    replies: ['Load defect frequency data →', 'Explain Hidden Factory / RTY', 'Show me the VSM data'],
  },
  {
    user: "Here is our defect data by type. Dimensional errors are by far the biggest category.",
    score: 7,
    method: 'SIX_SIGMA',
    thinking: [
      'Defect data received. Running Pareto analysis...',
      'Total defects: 380',
      'Dimensional Error: 148 (38.9%) ← vital few, primary target',
      'Surface Finish: 97 (25.5%)',
      'Top 2 = 64.5% of defects — Pareto principle confirmed',
      'Routing: Six Sigma — SPC + FMEA required',
      'SPC: need 25 subgroups from Machining A',
      'FMEA: RPN calc mandatory before any improvement action',
      'Preliminary scan: Final QC RPN ≈ 486 (S=9,O=6,D=9)',
      'current_info_score = 7 → 1 point from Solution Mode',
    ],
    panel: 'pareto',
    agent: [
      { type: 'text', text: '**Pareto Analysis Complete — Vital Few Identified:**\n• Dimensional Error: 148 units (38.9%)\n• Surface Finish: 97 units (25.5%)\n• **Top 2 = 64.5% of all defects**\n\nResources must concentrate here — not spread across all 6 types.' },
      { type: 'stop', text: '⛔ STOP-GATE STILL ACTIVE — Score 7/10. Two conditions unmet.' },
      { type: 'text', text: '**1. SPC Required:** Control chart preview shows 2 Special Cause violations (subgroups 12 & 19). A process not in statistical control cannot have Cpk calculated.\n\n**2. FMEA Required:** Preliminary scan → Final QC Inspector Drift = **RPN 486** (S=9, O=6, D=9). Poka-Yoke is mandatory for any Severity ≥ 8.' },
      { type: 'assign', text: '📋 Upload 25-subgroup SPC data from Machining A + completed FMEA to reach Score 8.' },
    ],
    replies: ['Load SPC data + FMEA →', 'What is Cpk and why does stability matter first?', 'Explain RPN 486'],
  },
  {
    user: "Uploading 25-subgroup SPC data from Machining A and our completed FMEA now.",
    score: 8,
    method: 'SIX_SIGMA',
    thinking: [
      'SPC data: 25 subgroups received.',
      'Calculating control limits: UCL=58.4, LCL=35.6, CL=47.0',
      'Violation: Subgroup 12 = 61.2 → ABOVE UCL ✗',
      'Violation: Subgroup 19 = 63.8 → ABOVE UCL ✗',
      'Root cause hypothesis: progressive tool wear (no TPM)',
      'FMEA loaded. Highest RPN: Final QC = 486 (S=9,O=6,D=9)',
      'Poka-Yoke MANDATORY — Severity 9, cannot use manual inspection',
      'All Stop-Gate conditions satisfied.',
      '→ current_info_score = 8 — SOLUTION MODE UNLOCKED 🔓',
    ],
    panel: 'fmea',
    agent: [
      { type: 'unlock', text: '🔓 INFO SCORE 8/10 — ALL STOP-GATE CONDITIONS SATISFIED. IMPROVEMENT ROADMAP UNLOCKED.' },
      { type: 'text', text: '**Phase 1 — Stabilize (Six Sigma)**\n\n**Priority 1: Eliminate Special Cause at Machining A** (RPN 378)\nRoot cause: No TPM schedule → progressive tool wear\nAction: Statistical tool-change trigger at Cp degradation threshold\n\n**Priority 2: Mandatory Poka-Yoke** (RPN 486)\nFinal QC inspector drift CANNOT be resolved by adding inspectors.\nAction: Automated vision system or precision go/no-go fixture\n⚠️ You cannot advance to Control phase with Severity-9 relying on manual detection.' },
      { type: 'text', text: '**Phase 2 — Simplify Flow (Lean)**\nOnce process is in statistical control:\n• Kanban design for Machining A (lead time stability required first — current σ=2.1 days)\n• VSM Future State: target 65% Lead Time reduction\n• Takt Time recalculation after rework loop eliminated' },
      { type: 'text', text: '**Sigma Level Projection:**\n| | Current | Target |\n|---|---|---|\n| DPMO | ~41,200 | <6,800 |\n| Sigma | 3.2σ | ≥4.0σ |\n| Cpk | ~0.87 | ≥1.33 |\n| RTY | ~61% | ≥85% |' },
    ],
    replies: ['Generate PDF Work Order', 'Calculate Kanban bins', 'View full FMEA priorities'],
  },
];

const FAILURE_CASES = [
  {
    label: '🏭 Hidden Factory Case',
    user: 'A foundry reported high First-Pass Yields but costs were double. Sigma = 2.33. Why?',
    thinking: ['RTY vs FPY discrepancy analysis', 'Sigma 2.33 → DPMO ≈ 100,000', 'Cost 2× theoretical → undocumented rework', 'Hidden Factory: rework loops excluded from tracking', 'RTY = ∏FPYᵢ reveals true throughput'],
    agent: [
      { type: 'text', text: '**Failure Analysis: The Hidden Factory**\n\nFlawed castings were returned for grinding/welding *without documentation*. Management tracked final FPY but never measured per-step yield.\n\nRTY = ∏FPYᵢ\n\nEven 95% yield at each of 6 steps:\n**RTY = 0.95⁶ = 73.5%**\n\nThe 26.5% hidden rework consumed 30% more energy and labor than output justified.' },
      { type: 'stop', text: '⚠️ Warning Signs: Informal rework piles near workstations. Capacity discrepancy: 30% more energy than output predicted. VSM showed 5-day process; actual = 14 days.' },
    ],
  },
  {
    label: '🔬 Tool Mismatch Case',
    user: 'A lab ran 5S/VSM to fix report delays. Workspace cleaner, but lead times unchanged. Why?',
    thinking: ['Lean tools applied to a variation problem', '5S/VSM = flow tools — no statistical depth', 'Lab delays → driven by retest rates, not layout', 'Six Sigma (Gage R&R, DOE) required', 'Clean Lab Paradox: high org score, zero lead time improvement'],
    agent: [
      { type: 'text', text: '**Failure Analysis: Tool Mismatch**\n\nThe delays were driven by a 5% retest rate caused by reagent inconsistency and equipment calibration drift — issues of *process variation*, not physical flow.\n\nLean tools have no statistical mechanism to identify interaction effects between "Material" and "Measurement" variables.' },
      { type: 'stop', text: '⚠️ The "Speed of Implementation" Trap: applying only Lean to a variation problem merely accelerates a broken process. Gage R&R + DOE were required.' },
    ],
  },
  {
    label: '📊 Sampling Bias Case',
    user: 'A bank redesigned staffing from a 2-week study. Friday complaints hit all-time high. Why?',
    thinking: ['Insufficient sample: 2 weeks, weekday mornings only', 'Missed Friday afternoons and month-end peaks', 'Reported avg: 7.8 min | True 95th pct Friday: 18.5 min', 'Non-normal distribution: outliers excluded as anomalies', 'Convenience sampling → dishonest baseline'],
    agent: [
      { type: 'text', text: '**Failure Analysis: Temporal Sampling Bias**\n\nData was collected only on weekday mornings, missing Friday afternoon surges and month-end cycles. The staffing model was optimized for "normal" days — not the days customers actually complain.\n\nReported mean: 7.8 min | True 95th percentile (Fridays): **18.5 min**' },
      { type: 'stop', text: '⚠️ LeanSigma IQ Stop-Gate: 25 subgroups must include ALL operating conditions — Fridays, month-ends, seasonal peaks. "Slow days" are symptoms of a non-normal distribution, not outliers to exclude.' },
    ],
  },
];

// ─── PDF GENERATION ──────────────────────────────────────────
function generateWorkOrderPDF(step, method) {
  const templates = {
    vsm: {
      title: 'Field Assignment: Value Stream Diagnostic',
      objective: 'Create a baseline "Current State" map and calculate the Value-Added Ratio.',
      method: 'Walk the process from Shipping back to Supplier. For every process step, directly observe and record C/T, C/O, Uptime, and WIP count. Do NOT use ERP estimates — Gemba observations only.',
      table: `<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse">
        <tr style="background:#1e3a5f;color:white"><th>Process Step</th><th>C/T (sec)</th><th>C/O (min)</th><th>Uptime (%)</th><th>WIP Count</th></tr>
        ${['Receiving','Inspection','Machining A','Assembly','Final QC','Shipping'].map(s=>`<tr><td>${s}</td><td></td><td></td><td></td><td></td></tr>`).join('')}
      </table>`,
      stopGate: 'PAUSED: We cannot identify Kaizen Bursts until Total Lead Time and Total Cycle Time are calculated.',
    },
    pareto: {
      title: 'Field Assignment: Defect Stratification Check Sheet',
      objective: 'Identify the "vital few" defect types responsible for the majority of quality failures (80/20 rule).',
      method: 'For one full production shift, categorize every defect as it occurs. Do not guess or batch-record at end of shift — real-time tally only.',
      table: `<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse">
        <tr style="background:#1e3a5f;color:white"><th>Defect Type / Problem</th><th>Tally (Occurrences)</th><th>Total Frequency</th></tr>
        ${['Dimensional Error','Surface Finish','Misalignment','Missing Component','Labeling Error','Other'].map(d=>`<tr><td>${d}</td><td></td><td></td></tr>`).join('')}
      </table>`,
      stopGate: 'PAUSED: Without empirical frequency data, we risk dedicating resources to the trivial many rather than the vital few.',
    },
    spc: {
      title: 'Field Assignment: Process Stability Study (SPC)',
      objective: 'Determine if the current process is statistically stable before performing capability analysis.',
      method: 'Collect 25 subgroups (n=5) from Machining A output. Do NOT adjust process settings during collection. Record any external events (maintenance, shift changes).',
      table: `<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse">
        <tr style="background:#1e3a5f;color:white"><th>Interval</th><th>S1</th><th>S2</th><th>S3</th><th>S4</th><th>S5</th><th>Mean</th><th>Range</th></tr>
        ${Array.from({length:25},(_,i)=>`<tr><td>${i+1}</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`).join('')}
      </table>`,
      stopGate: 'PAUSED: Cpk cannot be calculated until Process Stability is proven. A process not in statistical control has no predictable capability.',
    },
    fmea: {
      title: 'Field Assignment: Risk Identification Study (FMEA)',
      objective: 'Quantify process risks via RPN = Severity × Occurrence × Detection before implementing changes.',
      method: 'Walk each process step. Brainstorm potential failure modes. Score S, O, D on 1–10 scales using standardized criteria. Flag any S ≥ 9 regardless of total RPN.',
      table: `<table border="1" cellpadding="8" style="width:100%;border-collapse:collapse;font-size:11px">
        <tr style="background:#1e3a5f;color:white"><th>Step</th><th>Failure Mode</th><th>Effect</th><th>S</th><th>Cause</th><th>O</th><th>Control</th><th>D</th><th>RPN</th></tr>
        ${Array.from({length:6},()=>`<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`).join('')}
      </table>`,
      stopGate: 'PAUSED: No Improvement actions may be taken until RPNs are calculated to establish risk baselines.',
    },
  };

  const t = templates[step] || templates.vsm;
  const html = `<!DOCTYPE html><html><head><title>LeanSigma IQ — ${t.title}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; color: #1a1a2e; }
    h1 { color: #1e3a5f; font-size: 18px; border-bottom: 3px solid #3b82f6; padding-bottom: 8px; }
    h2 { color: #1e3a5f; font-size: 13px; margin-top: 18px; text-transform: uppercase; letter-spacing: 1px; }
    .meta { display: flex; gap: 20px; margin: 10px 0; font-size: 12px; color: #666; }
    .stop { background: #fef2f2; border: 2px solid #fca5a5; border-radius: 6px; padding: 10px 14px; margin-top: 20px; color: #991b1b; font-weight: bold; font-size: 12px; }
    table { border-color: #d1d5db; margin-top: 8px; }
    td, th { font-size: 12px; }
    .method-badge { background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    @media print { body { margin: 20px; } button { display: none; } }
  </style></head><body>
  <div style="display:flex;justify-content:space-between;align-items:center">
    <h1>🔷 LeanSigma IQ — ${t.title}</h1>
    <span class="method-badge">${method || 'HYBRID'}</span>
  </div>
  <div class="meta">
    <span>Date: ${new Date().toLocaleDateString()}</span>
    <span>Assigned by: LeanSigma IQ Agent</span>
    <span>Status: ACTIVE FIELD ASSIGNMENT</span>
  </div>
  <h2>1. Hypothesis / Objective</h2>
  <p style="font-size:13px">${t.objective}</p>
  <h2>2. Gemba Method</h2>
  <p style="font-size:13px">${t.method}</p>
  <h2>3. Data Entry Template</h2>
  ${t.table}
  <div class="stop">⛔ STOP-GATE WARNING — ${t.stopGate}</div>
  <div style="margin-top:30px;font-size:10px;color:#999;border-top:1px solid #e5e7eb;padding-top:10px">
    Generated by LeanSigma IQ • Analytical Rigor over Conversational Speed • Do not alter Stop-Gate conditions
  </div>
  <script>window.print();<\/script>
  </body></html>`;

  const w = window.open('', '_blank');
  if (w) { w.document.write(html); w.document.close(); }
}

// ─── SYSTEM PROMPT (Live Mode) ────────────────────────────────
const SYSTEM_PROMPT = `You are LeanSigma IQ, an AI Master Black Belt collaborator. You maintain absolute methodological rigor while being empathetic and concise.

CORE RULES:
1. Maintain current_info_score (1-10). Start at 1. Advance only when user provides quantified data.
2. Score 1-4 = Define/Diagnostic (Socratic questions only). Score 5-7 = Measure/Analyze (gap analysis). Score 8-10 = Improve/Control (prescriptive solutions).
3. NEVER provide an Improvement Roadmap if score < 8. Issue a Field Assignment instead.
4. Always begin response with a [Thinking] block showing your internal logic.

METHODOLOGY ROUTING:
- "Slow/Clutter/Wait/Flow/Lead Time" → Lean (VSM, 5S, Kanban)
- "Errors/Defects/Inconsistency/Variation" → Six Sigma (SPC, FMEA, Gage R&R)
- Both triggers → Hybrid: "Simplify before Stabilize" mandate

HIDDEN FACTORY: Always scan data for repeated IDs/rework loops. If found, pivot from Lean to Six Sigma.

STOP-GATE CONDITIONS (per tool):
- VSM: Need C/T, C/O, Uptime, WIP for all steps
- SPC: Need 25 subgroups before calculating Cpk
- FMEA: Need RPN scores before any improvement action
- Kanban: Need stable lead time (low σ) before implementation
- Poka-Yoke: Mandatory if any FMEA Severity ≥ 8

PERSONA: Insightful, concise, professional empathy with dry wit. You are a peer mentor, not a rigid lecturer. Use markdown for responses. Never skip the Stop-Gate check.`;

// ─── SUB-COMPONENTS ───────────────────────────────────────────
function ScoreHUD({ score, phaseIdx }) {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? C.green : score >= 6 ? C.amber : C.blue;
  const phase = PHASES[phaseIdx];
  return (
    <div style={{ ...s.card, textAlign: 'center', position: 'relative' }}>
      <div style={{ fontSize: 11, color: C.muted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Info Score</div>
      <div style={{ fontSize: 42, fontWeight: 800, color, lineHeight: 1, letterSpacing: -2 }}>
        {score}<span style={{ fontSize: 20, color: C.muted, fontWeight: 400 }}>/10</span>
      </div>
      <div style={{ margin: '8px 0 6px', height: 6, background: C.surface, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.6s ease, background 0.4s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        {PHASES.map((p, i) => (
          <div key={p} style={{ fontSize: 9, color: i <= phaseIdx ? PHASE_COLORS[i] : C.muted, fontWeight: i === phaseIdx ? 700 : 400 }}>{p}</div>
        ))}
      </div>
      <span style={s.badge(PHASE_COLORS[phaseIdx])}>{phase} Phase</span>
    </div>
  );
}

function MethodBadge({ method }) {
  if (!method) return null;
  const map = { LEAN: [C.blue, '⚡ LEAN'], SIX_SIGMA: [C.purple, 'σ SIX SIGMA'], HYBRID: [C.amber, '⚙ HYBRID'] };
  const [color, label] = map[method] || [C.muted, method];
  return <span style={s.badge(color)}>{label}</span>;
}

function ThinkingBlock({ thoughts, isThinking }) {
  const [open, setOpen] = useState(true);
  if (!thoughts.length && !isThinking) return null;
  return (
    <div style={{ ...s.card, marginTop: 8, fontSize: 11 }}>
      <button onClick={() => setOpen(o => !o)} style={{ ...s.outlineBtn, width: '100%', textAlign: 'left', padding: '2px 0', border: 'none', color: C.blueLight, fontSize: 11, fontWeight: 600, background: 'transparent' }}>
        {open ? '▾' : '▸'} AGENT THINKING BLOCK {isThinking ? '●' : ''}
      </button>
      {open && (
        <div style={{ marginTop: 6, maxHeight: 140, overflowY: 'auto' }}>
          {thoughts.map((t, i) => (
            <div key={i} style={{ color: t.startsWith('→') || t.startsWith('⛔') || t.startsWith('⚠️') ? C.amber : C.muted, padding: '1px 0', lineHeight: 1.5 }}>
              <span style={{ color: C.border, marginRight: 4 }}>{String(i + 1).padStart(2, '0')}</span>{t}
            </div>
          ))}
          {isThinking && (
            <div style={{ color: C.blueLight, marginTop: 4 }}>
              <span style={{ marginRight: 2 }}>●</span><span style={{ opacity: 0.6 }}>●</span><span style={{ opacity: 0.3 }}>●</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MsgBlock({ parts, methodology }) {
  return (
    <div style={{ ...s.card, marginBottom: 6, fontSize: 12, lineHeight: 1.7 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: 14 }}>🔷</span>
        <span style={{ color: C.blueLight, fontWeight: 700, fontSize: 11 }}>LeanSigma IQ</span>
        {methodology && <MethodBadge method={methodology} />}
      </div>
      {parts.map((p, i) => {
        if (p.type === 'stop') return (
          <div key={i} style={s.stopGate}>
            <span style={{ color: C.red, fontSize: 11, fontWeight: 700 }}>{p.text}</span>
          </div>
        );
        if (p.type === 'unlock') return (
          <div key={i} style={s.unlocked}>
            <span style={{ color: C.green, fontSize: 12, fontWeight: 700 }}>{p.text}</span>
          </div>
        );
        if (p.type === 'assign') return (
          <div key={i} style={{ background: '#1d3a5f22', border: `1px solid ${C.blue}44`, borderRadius: 6, padding: '8px 10px', margin: '6px 0' }}>
            <span style={{ color: C.blueLight, fontSize: 11 }}>{p.text}</span>
          </div>
        );
        return (
          <div key={i} style={{ marginTop: 6, color: C.text, whiteSpace: 'pre-wrap' }}>
            {p.text.split(/\*\*(.*?)\*\*/g).map((seg, j) =>
              j % 2 === 1 ? <strong key={j} style={{ color: C.text }}>{seg}</strong> : seg
            )}
          </div>
        );
      })}
    </div>
  );
}

function UserMsg({ text }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
      <div style={{ background: C.blue + '33', border: `1px solid ${C.blue}55`, borderRadius: 8, padding: '8px 12px', maxWidth: '85%', fontSize: 12, color: C.text, lineHeight: 1.5 }}>
        {text}
      </div>
    </div>
  );
}

// ─── DATA CANVAS PANELS ───────────────────────────────────────
function VSMPanel() {
  const totalLT = (PROCESS_STEPS.reduce((a, s) => a + s.wip, 0) / 42).toFixed(1);
  const totalVA = (PROCESS_STEPS.filter(s => !s.rework).reduce((a, s) => a + s.ct, 0) / 3600).toFixed(1);
  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        {[['Total Lead Time', `${totalLT} days`, C.amber], ['VA Time', `${totalVA} hrs`, C.blue], ['VA Ratio', '2.8%', C.red], ['WIP (Total)', '692 units', C.purple]].map(([l, v, c]) => (
          <div key={l} style={{ flex: 1, ...s.card, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: C.muted, marginBottom: 2 }}>{l}</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: c }}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: C.surface2 }}>
              {['Process Step','C/T (sec)','C/O (min)','Uptime %','WIP','Status'].map(h => (
                <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: C.muted, fontWeight: 600, fontSize: 11, borderBottom: `1px solid ${C.border}` }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PROCESS_STEPS.map((row, i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${C.border}22`, background: row.rework ? '#ef444408' : row.bottleneck ? '#f59e0b08' : 'transparent' }}>
                <td style={{ padding: '7px 10px', color: C.text, fontWeight: row.bottleneck ? 700 : 400 }}>{row.step}</td>
                <td style={{ padding: '7px 10px', color: C.text }}>{row.ct}</td>
                <td style={{ padding: '7px 10px', color: C.text }}>{row.co}</td>
                <td style={{ padding: '7px 10px', color: row.uptime < 75 ? C.red : row.uptime < 85 ? C.amber : C.green }}>{row.uptime}%</td>
                <td style={{ padding: '7px 10px', color: row.wip > 150 ? C.red : row.wip > 80 ? C.amber : C.text, fontWeight: row.wip > 150 ? 700 : 400 }}>{row.wip}</td>
                <td style={{ padding: '7px 10px' }}>
                  {row.rework && <span style={s.badge(C.red)}>🔁 REWORK</span>}
                  {row.bottleneck && <span style={s.badge(C.amber)}>⚠ BOTTLENECK</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ ...s.stopGate, marginTop: 14 }}>
        <span style={{ color: C.red, fontSize: 11, fontWeight: 700 }}>🚨 HIDDEN FACTORY: Repeated WO IDs detected — WO-1042 ×3, WO-1087 ×2, WO-1156 ×2. Methodology pivot to Six Sigma required.</span>
      </div>
    </div>
  );
}

function ParetoPanel() {
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', fontSize: 11 }}>
        <div style={{ color: C.text, fontWeight: 700 }}>{payload[0]?.payload.type}</div>
        <div style={{ color: C.blue }}>Count: {payload[0]?.value}</div>
        <div style={{ color: C.amber }}>Cumulative: {payload[0]?.payload.cum}%</div>
      </div>
    );
  };
  return (
    <div style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        {[['Total Defects','380',C.red],['Top 2 Types','64.5%',C.amber],['Primary Target','Dim. Error',C.blue]].map(([l,v,c])=>(
          <div key={l} style={{flex:1,...s.card,textAlign:'center'}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:2}}>{l}</div>
            <div style={{fontSize:16,fontWeight:700,color:c}}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={DEFECT_DATA} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
            <XAxis dataKey="short" tick={{ fill: C.muted, fontSize: 10 }} />
            <YAxis yAxisId="left" tick={{ fill: C.muted, fontSize: 10 }} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fill: C.amber, fontSize: 10 }} unit="%" />
            <Tooltip content={<CustomTooltip />} />
            <Bar yAxisId="left" dataKey="count" radius={[3, 3, 0, 0]}>
              {DEFECT_DATA.map((_, i) => <Cell key={i} fill={i < 2 ? C.blue : C.border} />)}
            </Bar>
            <Line yAxisId="right" type="monotone" dataKey="cum" stroke={C.amber} strokeWidth={2} dot={{ r: 3, fill: C.amber }} />
            <ReferenceLine yAxisId="right" y={80} stroke={C.green} strokeDasharray="4 4" label={{ value: '80%', fill: C.green, fontSize: 10 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ControlPanel() {
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div style={{ background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', fontSize: 11 }}>
        <div style={{ color: C.text, fontWeight: 700 }}>Subgroup {d?.sg}</div>
        <div style={{ color: d?.special ? C.red : C.blue }}>Mean: {d?.mean} {d?.special ? '← SPECIAL CAUSE' : ''}</div>
        <div style={{ color: C.muted }}>UCL: {d?.ucl} | LCL: {d?.lcl}</div>
      </div>
    );
  };
  return (
    <div style={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        {[['UCL','58.4',C.red],['Center Line','47.0',C.blue],['LCL','35.6',C.red],['Violations','2 pts',C.amber]].map(([l,v,c])=>(
          <div key={l} style={{flex:1,...s.card,textAlign:'center'}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:2}}>{l}</div>
            <div style={{fontSize:16,fontWeight:700,color:c}}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={CONTROL_DATA} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
            <XAxis dataKey="sg" tick={{ fill: C.muted, fontSize: 10 }} label={{ value: 'Subgroup', position: 'insideBottom', offset: -10, fill: C.muted, fontSize: 10 }} />
            <YAxis domain={[30, 70]} tick={{ fill: C.muted, fontSize: 10 }} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={58.4} stroke={C.red} strokeDasharray="4 4" label={{ value: 'UCL', position: 'right', fill: C.red, fontSize: 10 }} />
            <ReferenceLine y={47.0} stroke={C.blue} strokeDasharray="4 4" label={{ value: 'CL', position: 'right', fill: C.blue, fontSize: 10 }} />
            <ReferenceLine y={35.6} stroke={C.red} strokeDasharray="4 4" label={{ value: 'LCL', position: 'right', fill: C.red, fontSize: 10 }} />
            <Line type="monotone" dataKey="mean" stroke={C.blueLight} strokeWidth={2} dot={(props) => {
              const { cx, cy, payload } = props;
              return <circle key={cx} cx={cx} cy={cy} r={payload.special ? 6 : 3} fill={payload.special ? C.red : C.blueLight} stroke={payload.special ? C.red : 'none'} />;
            }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div style={{ ...s.stopGate, marginTop: 8 }}>
        <span style={{ color: C.red, fontSize: 11, fontWeight: 700 }}>⚠ SPECIAL CAUSE VIOLATIONS at subgroups 12 (61.2) and 19 (63.8). Root cause: progressive tool wear — no TPM schedule. Cpk cannot be calculated until process is in control.</span>
      </div>
    </div>
  );
}

function FMEAPanel() {
  const getRPNColor = (rpn) => rpn >= 400 ? C.red : rpn >= 300 ? C.amber : C.text;
  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        {[['Highest RPN','486',C.red],['Critical S≥9','2 items',C.red],['Poka-Yoke Req.','Mandatory',C.amber]].map(([l,v,c])=>(
          <div key={l} style={{flex:1,...s.card,textAlign:'center'}}>
            <div style={{fontSize:10,color:C.muted,marginBottom:2}}>{l}</div>
            <div style={{fontSize:16,fontWeight:700,color:c}}>{v}</div>
          </div>
        ))}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ background: C.surface2 }}>
            {['Step','Failure Mode','Effect','S','Cause','O','Detection','D','RPN'].map(h => (
              <th key={h} style={{ padding: '8px 8px', textAlign: 'left', color: C.muted, fontWeight: 600, fontSize: 10, borderBottom: `1px solid ${C.border}` }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {FMEA_DATA.sort((a, b) => b.rpn - a.rpn).map((row, i) => (
            <tr key={i} style={{ borderBottom: `1px solid ${C.border}22`, background: row.rpn >= 400 ? '#ef444408' : 'transparent' }}>
              <td style={{ padding: '7px 8px', color: C.text }}>{row.step}</td>
              <td style={{ padding: '7px 8px', color: C.text }}>{row.mode}</td>
              <td style={{ padding: '7px 8px', color: C.muted }}>{row.effect}</td>
              <td style={{ padding: '7px 8px', color: row.s >= 9 ? C.red : row.s >= 7 ? C.amber : C.text, fontWeight: 700 }}>{row.s}</td>
              <td style={{ padding: '7px 8px', color: C.muted }}>{row.cause}</td>
              <td style={{ padding: '7px 8px', color: C.text }}>{row.o}</td>
              <td style={{ padding: '7px 8px', color: C.muted }}>{row.detection}</td>
              <td style={{ padding: '7px 8px', color: row.d >= 8 ? C.red : C.text, fontWeight: 700 }}>{row.d}</td>
              <td style={{ padding: '7px 8px', fontWeight: 700, color: getRPNColor(row.rpn) }}>{row.rpn}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ ...s.stopGate, marginTop: 12 }}>
        <span style={{ color: C.red, fontSize: 11, fontWeight: 700 }}>⛔ Poka-Yoke MANDATORY: Final QC RPN 486 has Severity=9. You cannot proceed to Control phase with manual inspection on a Severity-9 failure mode.</span>
      </div>
    </div>
  );
}

function RoadmapPanel({ score }) {
  if (score < 8) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔒</div>
        <div style={{ fontSize: 16, fontWeight: 700, color: C.muted, marginBottom: 8 }}>Improvement Roadmap Locked</div>
        <div style={{ fontSize: 13, color: C.muted, maxWidth: 300 }}>Info Score must reach 8/10 to unlock. Complete the field assignments and upload required data.</div>
        <div style={{ marginTop: 16, ...s.card, width: 280 }}>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 8 }}>Required to unlock:</div>
          {['Defect stratification (Pareto)', '25-subgroup SPC stability study', 'FMEA with RPN calculations'].map((item, i) => (
            <div key={i} style={{ color: score >= [5, 7, 8][i] ? C.green : C.amber, fontSize: 11, padding: '3px 0' }}>
              {score >= [5, 7, 8][i] ? '✓' : '○'} {item}
            </div>
          ))}
        </div>
      </div>
    );
  }
  const items = [
    { priority: 1, phase: 'Six Sigma', title: 'Eliminate Special Cause — Machining A', rpn: 378, color: C.amber, action: 'Implement statistical tool-change trigger at Cp degradation threshold. Eliminates 2 SPC violations.', metric: 'Process → In-Control (Cpk calculable)' },
    { priority: 2, phase: 'Six Sigma', title: 'Mandatory Poka-Yoke — Final QC', rpn: 486, color: C.red, action: 'Install automated vision system or precision go/no-go fixture. Manual inspection cannot remain.', metric: 'RPN 486 → target RPN < 100' },
    { priority: 3, phase: 'Lean', title: 'Kanban Design — Machining A', rpn: null, color: C.blue, action: 'After lead time σ stabilizes, implement pull system. K = (42 × L + S) / 20. Target WIP reduction ≥30%.', metric: 'WIP: 203 units → < 80 units' },
    { priority: 4, phase: 'Lean', title: 'VSM Future State', rpn: null, color: C.green, action: 'Redesign material flow after rework loop elimination. Target 65% Lead Time reduction.', metric: 'Lead Time: 14.2 days → < 5 days' },
  ];
  const metrics = [['DPMO','~41,200','< 6,800',C.red,C.green],['Sigma Level','3.2σ','≥ 4.0σ',C.amber,C.green],['Cpk','~0.87','≥ 1.33',C.red,C.green],['RTY','~61%','≥ 85%',C.amber,C.green]];
  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ ...s.unlocked, marginBottom: 14 }}>
        <span style={{ color: C.green, fontWeight: 700, fontSize: 12 }}>🔓 IMPROVEMENT ROADMAP UNLOCKED — Info Score 8/10. All Stop-Gate conditions satisfied.</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {metrics.map(([label, curr, target, cc, tc]) => (
          <div key={label} style={{ flex: 1, ...s.card, textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: C.muted, marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: cc }}>{curr}</div>
            <div style={{ fontSize: 9, color: C.muted }}>→</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: tc }}>{target}</div>
          </div>
        ))}
      </div>
      {items.map((item) => (
        <div key={item.priority} style={{ ...s.card, marginBottom: 10, borderLeft: `3px solid ${item.color}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ background: item.color, color: '#fff', borderRadius: '50%', width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>{item.priority}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.text }}>{item.title}</span>
            <span style={s.badge(item.color === C.blue || item.color === C.green ? C.blue : C.purple)}>{item.phase}</span>
            {item.rpn && <span style={s.badge(C.red)}>RPN {item.rpn}</span>}
          </div>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{item.action}</div>
          <div style={{ fontSize: 11, color: C.green }}>Expected: {item.metric}</div>
        </div>
      ))}
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────
export default function LeanSigmaIQ() {
  const [messages, setMessages] = useState([]);
  const [thinking, setThinking] = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [score, setScore] = useState(1);
  const [methodology, setMethodology] = useState(null);
  const [demoIdx, setDemoIdx] = useState(0);
  const [activePanel, setActivePanel] = useState('vsm');
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('demo');
  const [apiKey, setApiKey] = useState('');
  const [quickReplies, setQuickReplies] = useState([]);
  const chatEndRef = useRef(null);

  useEffect(() => {
    setMessages([{
      type: 'agent',
      parts: [
        { type: 'text', text: "Welcome. I'm LeanSigma IQ — your AI Master Black Belt collaborator.\n\nI operate on the principle of **Analytical Rigor over Conversational Speed**. I will not prescribe solutions until the data justifies them." },
        { type: 'text', text: 'Tell me about your process problem, or choose a **Demo Scenario** to see a full DMAIC walkthrough.' },
      ],
      methodology: null,
    }]);
    setQuickReplies(['Start Demo: Production Line →', 'Failure Analysis: Hidden Factory', 'Failure Analysis: Tool Mismatch']);
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const addMessage = useCallback((type, content, method) => {
    setMessages(prev => [...prev, { type, ...content, methodology: method }]);
  }, []);

  const runDemoStep = useCallback(async (step) => {
    addMessage('user', { text: step.user }, null);
    setIsThinking(true);
    setThinking([]);

    for (let i = 0; i < step.thinking.length; i++) {
      await new Promise(r => setTimeout(r, 180));
      setThinking(prev => [...prev, step.thinking[i]]);
    }

    await new Promise(r => setTimeout(r, 300));
    setIsThinking(false);
    setScore(step.score);
    setMethodology(step.method);
    setActivePanel(step.panel);
    addMessage('agent', { parts: step.agent }, step.method);
    setQuickReplies(step.replies || []);
  }, [addMessage]);

  const handleDemoNext = useCallback(() => {
    if (demoIdx < DEMO_STEPS.length) {
      runDemoStep(DEMO_STEPS[demoIdx]);
      setDemoIdx(i => i + 1);
    }
  }, [demoIdx, runDemoStep]);

  const handleFailureCase = useCallback(async (fc) => {
    addMessage('user', { text: fc.user }, null);
    setIsThinking(true);
    setThinking([]);
    for (const t of fc.thinking) {
      await new Promise(r => setTimeout(r, 160));
      setThinking(prev => [...prev, t]);
    }
    await new Promise(r => setTimeout(r, 300));
    setIsThinking(false);
    addMessage('agent', { parts: fc.agent }, null);
    setQuickReplies(['Start Demo: Production Line →', 'Another Failure Case?']);
  }, [addMessage]);

  const handleLiveMode = useCallback(async (userMsg) => {
    addMessage('user', { text: userMsg }, null);
    setIsThinking(true);
    setThinking(['Calling Claude API...', 'Applying LeanSigma IQ scoring protocol...']);
    try {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01', 'content-type': 'application/json', 'anthropic-dangerous-direct-browser-access': 'true' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-6',
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: [{ role: 'user', content: userMsg }],
        }),
      });
      const data = await res.json();
      const text = data.content?.[0]?.text || 'No response received.';
      setIsThinking(false);
      addMessage('agent', { parts: [{ type: 'text', text }] }, null);
    } catch (e) {
      setIsThinking(false);
      addMessage('agent', { parts: [{ type: 'stop', text: `API Error: ${e.message}` }] }, null);
    }
    setQuickReplies([]);
  }, [addMessage, apiKey]);

  const handleSend = useCallback((msg) => {
    const text = (msg || input).trim();
    if (!text) return;
    setInput('');

    if (text === 'Start Demo: Production Line →') { handleDemoNext(); return; }
    const fc = FAILURE_CASES.find(f => text.includes(f.label) || text === `Failure Analysis: ${f.label.replace(/^[^ ]+ /, '')}`);
    if (fc) { handleFailureCase(fc); return; }

    const demoStep = DEMO_STEPS.find((_, i) => i === demoIdx && DEMO_STEPS[demoIdx]?.replies?.includes(text));
    if (demoStep || (demoIdx < DEMO_STEPS.length && mode === 'demo')) {
      if (text.includes('→') || text.startsWith('Upload') || text.startsWith('Load')) { handleDemoNext(); return; }
    }

    if (text === 'Generate PDF Work Order') { generateWorkOrderPDF(activePanel, methodology); return; }
    if (text === 'Calculate Kanban bins') {
      addMessage('user', { text }, null);
      addMessage('agent', { parts: [{ type: 'stop', text: '⛔ Kanban BLOCKED: Lead time σ=2.1 days (CV>30%). Stabilize via SPC first.' }, { type: 'text', text: 'When stable: K = (42 × L + S) / C\n• d=42 units/day · L=3.8 days · S=15% · C=20 units\n**Preliminary K ≈ 11 bins** (pending stability)' }] }, methodology);
      return;
    }
    if (text.includes('FMEA') || text.includes('fmea')) { setActivePanel('fmea'); }
    if (text.includes('Pareto') || text.includes('pareto')) { setActivePanel('pareto'); }
    if (text.includes('control chart') || text.includes('SPC') || text.includes('stability')) { setActivePanel('spc'); }
    if (text.includes('roadmap') || text.includes('Roadmap')) { setActivePanel('roadmap'); }

    if (mode === 'live' && apiKey) { handleLiveMode(text); return; }

    addMessage('user', { text }, null);
    if (demoIdx < DEMO_STEPS.length && mode === 'demo') {
      setTimeout(() => handleDemoNext(), 400);
    } else {
      addMessage('agent', { parts: [{ type: 'text', text: "All demo scenarios complete. Switch to **Live Mode** with your Claude API key to continue with the full AI agent, or type a Failure Analysis case name." }] }, methodology);
    }
  }, [input, mode, apiKey, demoIdx, activePanel, methodology, addMessage, handleDemoNext, handleFailureCase, handleLiveMode]);

  const PANEL_TABS = [
    { id: 'vsm', label: 'VSM' },
    { id: 'pareto', label: 'Pareto' },
    { id: 'spc', label: 'SPC' },
    { id: 'fmea', label: 'FMEA' },
    { id: 'roadmap', label: score >= 8 ? '🔓 Roadmap' : '🔒 Roadmap' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: C.bg, color: C.text, fontFamily: "'Inter','Segoe UI',sans-serif" }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', background: C.surface, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
        <span style={{ fontSize: 20, fontWeight: 800, color: C.blueLight, letterSpacing: -0.5 }}>🔷 LeanSigma IQ</span>
        <span style={{ fontSize: 10, color: C.muted, borderLeft: `1px solid ${C.border}`, paddingLeft: 10 }}>Analytical Rigor over Conversational Speed</span>
        {methodology && <MethodBadge method={methodology} />}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {mode === 'live' && (
            <input value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="Claude API Key" type="password"
              style={{ background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '4px 10px', fontSize: 11, color: C.text, width: 180 }} />
          )}
          <button onClick={() => setMode(m => m === 'demo' ? 'live' : 'demo')}
            style={{ ...s.outlineBtn, color: mode === 'live' ? C.green : C.muted, borderColor: mode === 'live' ? C.green : C.border, fontSize: 11 }}>
            {mode === 'demo' ? '⚡ Demo Mode' : '🤖 Live Mode'}
          </button>
          <button onClick={() => generateWorkOrderPDF(activePanel, methodology)} style={{ ...s.btn(C.blue), fontSize: 11, padding: '5px 10px' }}>
            📋 PDF Work Order
          </button>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Left Pane */}
        <div style={{ ...s.pane, width: 380, flexShrink: 0 }}>
          <div style={{ padding: '12px 12px 0', flexShrink: 0 }}>
            <ScoreHUD score={score} phaseIdx={getPhase(score)} />
            <ThinkingBlock thoughts={thinking} isThinking={isThinking} />
          </div>
          {/* Chat */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
            {messages.map((msg, i) => (
              msg.type === 'user'
                ? <UserMsg key={i} text={msg.text} />
                : <MsgBlock key={i} parts={msg.parts} methodology={msg.methodology} />
            ))}
            <div ref={chatEndRef} />
          </div>
          {/* Quick Replies */}
          {quickReplies.length > 0 && (
            <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 6, flexShrink: 0 }}>
              {quickReplies.map((r, i) => (
                <button key={i} onClick={() => handleSend(r)}
                  style={{ ...s.outlineBtn, fontSize: 11, padding: '5px 10px', color: C.blueLight, borderColor: C.blue + '55' }}>
                  {r}
                </button>
              ))}
            </div>
          )}
          {/* Input */}
          <div style={{ padding: '8px 12px', borderTop: `1px solid ${C.border}`, display: 'flex', gap: 8, flexShrink: 0 }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder={mode === 'demo' ? 'Type or click a quick reply...' : 'Ask LeanSigma IQ (Live Mode)...'}
              style={{ flex: 1, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, padding: '8px 12px', fontSize: 12, color: C.text, outline: 'none' }} />
            <button onClick={() => handleSend()} style={s.btn()}>→</button>
          </div>
        </div>

        {/* Right Pane */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {/* Panel Tabs */}
          <div style={{ display: 'flex', gap: 2, padding: '8px 12px', background: C.surface, borderBottom: `1px solid ${C.border}`, flexShrink: 0 }}>
            {PANEL_TABS.map(tab => (
              <button key={tab.id} onClick={() => setActivePanel(tab.id)}
                style={{ padding: '6px 14px', fontSize: 11, fontWeight: 600, border: 'none', borderRadius: 6, cursor: 'pointer', background: activePanel === tab.id ? C.blue : 'transparent', color: activePanel === tab.id ? '#fff' : C.muted, transition: 'background 0.2s' }}>
                {tab.label}
              </button>
            ))}
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              {FAILURE_CASES.map(fc => (
                <button key={fc.label} onClick={() => handleFailureCase(fc)}
                  style={{ ...s.outlineBtn, fontSize: 10, padding: '4px 8px', color: C.amber, borderColor: C.amber + '44' }}>
                  {fc.label}
                </button>
              ))}
            </div>
          </div>
          {/* Active Panel */}
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
            {activePanel === 'vsm'     && <VSMPanel />}
            {activePanel === 'pareto'  && <ParetoPanel />}
            {activePanel === 'spc'     && <ControlPanel />}
            {activePanel === 'fmea'    && <FMEAPanel />}
            {activePanel === 'roadmap' && <RoadmapPanel score={score} />}
          </div>
        </div>
      </div>
    </div>
  );
}
