export const processSteps = [
  { step: "Receiving",    ct: 12, co: 0,  uptime: 98, wip: 45 },
  { step: "Inspection",   ct: 28, co: 5,  uptime: 82, wip: 112 },
  { step: "Machining A",  ct: 47, co: 35, uptime: 71, wip: 203 },
  { step: "Rework Loop",  ct: 38, co: 10, uptime: 65, wip: 88, isRework: true },
  { step: "Assembly",     ct: 62, co: 20, uptime: 78, wip: 156 },
  { step: "Final QC",     ct: 19, co: 0,  uptime: 90, wip: 67 },
  { step: "Shipping",     ct: 8,  co: 0,  uptime: 99, wip: 21 },
];

export const defectData = [
  { type: "Dimensional Error",   count: 148, fill: "#6366f1" },
  { type: "Surface Finish",      count: 97,  fill: "#8b5cf6" },
  { type: "Misalignment",        count: 74,  fill: "#a78bfa" },
  { type: "Missing Component",   count: 31,  fill: "#c4b5fd" },
  { type: "Labeling Error",      count: 18,  fill: "#ddd6fe" },
  { type: "Other",               count: 12,  fill: "#ede9fe" },
];

export const controlChartData = Array.from({ length: 25 }, (_, i) => {
  const base = 47;
  const noise = (Math.sin(i * 0.7) * 3) + (Math.random() - 0.5) * 4;
  const specialCause = (i === 11 || i === 18) ? 12 : 0;
  return {
    subgroup: i + 1,
    mean: parseFloat((base + noise + specialCause).toFixed(2)),
    ucl: 58.4,
    lcl: 35.6,
    cl:  47.0,
    isSpecial: i === 11 || i === 18,
  };
});

export const reworkIds = [
  "WO-1042", "WO-1087", "WO-1042", "WO-1103",
  "WO-1156", "WO-1087", "WO-1042", "WO-1201",
  "WO-1156", "WO-1230",
];

export const fmeaData = [
  { step: "Machining A", mode: "Tool Wear",       effect: "Dimensional OOT", s: 9, cause: "No TPM schedule",    o: 7, detection: "Manual gauge", d: 6, rpn: 378 },
  { step: "Assembly",    mode: "Wrong Torque",    effect: "Field Failure",   s: 8, cause: "No poka-yoke",      o: 5, detection: "Visual check", d: 7, rpn: 280 },
  { step: "Final QC",    mode: "Inspector Drift", effect: "Escape to field", s: 9, cause: "No Gage R&R",       o: 6, detection: "None",         d: 9, rpn: 486 },
  { step: "Inspection",  mode: "Missed defect",   effect: "Rework cost",     s: 6, cause: "Fatigue / volume",  o: 8, detection: "Re-inspect",   d: 5, rpn: 240 },
];

export const kanbanMetrics = {
  avgDemand: 42,
  leadTimeDays: 3.8,
  leadTimeStdDev: 2.1,
  safetyFactor: 0.15,
  containerCapacity: 20,
};
