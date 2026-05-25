"""
Synthetic data generation pipeline for Noruh Manufacturing quality history.
Generates 5 years of CNC telemetry, lab testing, packaging, and customer feedback data
with 5 injected anomalies per PRD Section 4 specifications.

Vectorized via numpy for fast generation on CPU — typically completes in <60s.
"""

import numpy as np
import pandas as pd
import duckdb
from datetime import datetime, timedelta, date

# ── Deterministic seed ────────────────────────────────────────────────────────
RNG = np.random.default_rng(42)

DB_PATH = "data/noruh_quality.db"

# ── Factory constants ─────────────────────────────────────────────────────────
START_DATE = date(2021, 1, 1)
END_DATE   = date(2025, 12, 31)

SHIFTS_PER_DAY  = 3
PARTS_PER_SHIFT = 40
TOOL_LIFE       = 400

MACHINE_CFG = {
    "Machine_A": {"part_type": "Top",  "rpm": 12000, "feed": 1500},
    "Machine_B": {"part_type": "Leg",  "rpm":  9000, "feed": 1200},
    "Machine_C": {"part_type": "Stand","rpm": 10000, "feed": 1400},
}

# Shift → operator pool (indices into OP-001..OP-008)
SHIFT_OP_POOL = {
    0: [1, 2, 3],
    1: [4, 5, 6],
    2: [7, 8],
}

PKG_OPS = ["PKG-001", "PKG-002", "PKG-003"]

# ── Anomaly date windows (as ordinal boundaries for fast vectorized comparison)
def _ord(d: date) -> int:
    return d.toordinal()

A1_LO, A1_HI = _ord(date(2022, 4,  1)), _ord(date(2022, 6, 30))   # ANOM-01
A2_LO, A2_HI = _ord(date(2023, 6,  1)), _ord(date(2023, 8, 31))   # ANOM-02
A3_LO, A3_HI = _ord(date(2024, 10, 1)), _ord(date(2024, 10, 31))  # ANOM-03
A5_LO, A5_HI = _ord(date(2025, 11, 1)), _ord(date(2025, 11, 14)) # ANOM-05


# ─────────────────────────────────────────────────────────────────────────────
# Build the full timestamp + metadata index upfront
# ─────────────────────────────────────────────────────────────────────────────

def _build_index() -> pd.DataFrame:
    """
    Returns a DataFrame with one row per (day, shift, machine, part_within_shift).
    ~657k rows total. All scheduling metadata is computed here vectorized.
    """
    all_days = pd.date_range(start=str(START_DATE), end=str(END_DATE), freq="D")
    n_days   = len(all_days)

    # Cartesian: day × shift × machine × part_slot
    # Total: n_days × 3 × 3 × 40
    machines = list(MACHINE_CFG.keys())
    n_machines = len(machines)
    total = n_days * SHIFTS_PER_DAY * n_machines * PARTS_PER_SHIFT

    day_idx      = np.repeat(np.arange(n_days),        SHIFTS_PER_DAY * n_machines * PARTS_PER_SHIFT)
    shift_idx    = np.tile(np.repeat(np.arange(SHIFTS_PER_DAY), n_machines * PARTS_PER_SHIFT), n_days)
    machine_idx  = np.tile(np.repeat(np.arange(n_machines), PARTS_PER_SHIFT), n_days * SHIFTS_PER_DAY)
    part_slot    = np.tile(np.arange(PARTS_PER_SHIFT), n_days * SHIFTS_PER_DAY * n_machines)

    # Base timestamp: day date + shift start hour + part offset in 8h window
    shift_start_hours = np.array([6, 14, 22])   # 06:00 / 14:00 / 22:00
    day_ns   = all_days.values.astype("datetime64[ns]")
    base_day = day_ns[day_idx]
    shift_h  = shift_start_hours[shift_idx].astype("timedelta64[h]")
    part_min = ((part_slot / PARTS_PER_SHIFT) * 480).astype(int)
    part_td  = part_min.astype("timedelta64[m]")
    timestamps = base_day + shift_h + part_td

    # Day ordinal (for anomaly window masking)
    day_ord = np.array([d.toordinal() for d in all_days.date])[day_idx]

    # Assign operators per shift (vectorized pick from pool)
    # Night shift (2) on Machine B/C gets OP-007 preferentially for ANOM-03 window
    op_choices = np.empty(total, dtype="U7")
    for si in range(SHIFTS_PER_DAY):
        pool = SHIFT_OP_POOL[si]
        mask = shift_idx == si
        picks = RNG.integers(0, len(pool), size=mask.sum())
        op_choices[mask] = np.array([f"OP-{p:03d}" for p in picks], dtype="U7")[
            RNG.integers(0, len(pool), size=mask.sum())
        ]
        op_choices[mask] = np.array([f"OP-{pool[p]:03d}" for p in picks])

    # Part serial counter (global)
    serial_nums = np.arange(1, total + 1)
    ts_dates    = timestamps.astype("datetime64[D]").astype(object)
    serials = np.array(
        [f"PART-{str(d).replace('-', '')}-{n:05d}"
         for d, n in zip(ts_dates, serial_nums)]
    )

    return pd.DataFrame({
        "serial":      serials,
        "timestamp":   timestamps,
        "day_ord":     day_ord,
        "day_idx":     day_idx,
        "shift_idx":   shift_idx,
        "machine_idx": machine_idx,
        "part_slot":   part_slot,
        "operator_id": op_choices,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Generate cnc_telemetry columns
# ─────────────────────────────────────────────────────────────────────────────

def _build_cnc(idx: pd.DataFrame) -> pd.DataFrame:
    n = len(idx)
    machines = list(MACHINE_CFG.keys())

    machine_ids  = np.array([machines[i] for i in idx["machine_idx"]])
    part_types   = np.array([MACHINE_CFG[m]["part_type"] for m in machine_ids])
    nominal_rpm  = np.array([MACHINE_CFG[m]["rpm"]  for m in machine_ids], dtype=float)
    nominal_feed = np.array([MACHINE_CFG[m]["feed"] for m in machine_ids], dtype=float)

    spindle = np.round(nominal_rpm  * RNG.uniform(0.98, 1.02, n), 1)
    feed    = np.round(nominal_feed * RNG.uniform(0.99, 1.01, n), 1)

    # ── Tool age: reset every TOOL_LIFE parts per machine, reset on rejection ──
    # We track tool age per machine sequentially — must stay serial for resets.
    # Vectorize the modulo-reset: approximate with cumcount mod TOOL_LIFE,
    # then apply exact breakage resets in a second pass.
    tool_age = np.empty(n, dtype=int)
    counters = {m: 0 for m in machines}
    for i, mi in enumerate(idx["machine_idx"]):
        m = machines[mi]
        counters[m] += 1
        if counters[m] > TOOL_LIFE:
            counters[m] = 1
        tool_age[i] = counters[m]

    # ── Vibration: base ramp + noise ──────────────────────────────────────────
    base_vib   = 0.2 + (tool_age / TOOL_LIFE) * 2.0
    noise_vib  = RNG.normal(0, 0.15, n)
    # Spike probability rises near end-of-life
    spike_mask = (tool_age > 350) & (RNG.random(n) < 0.015)
    vibration  = np.where(spike_mask,
                          RNG.uniform(3.6, 5.0, n),
                          np.maximum(0.1, base_vib + noise_vib))
    vibration  = np.round(vibration, 4)

    # ── ANOM-04: catastrophic rejection (vibration > 3.5g) ───────────────────
    anom04_mask = vibration > 3.5
    part_status = np.where(anom04_mask, "COMPLETED_REJECTED", "COMPLETED_PASSED")

    # Reset tool_age to 0 on rejection (approximation: set counter to 0,
    # downstream tables skip these rows so the counter reset is cosmetic here)
    tool_age[anom04_mask] = 0

    # ── ANOM-03: OP-007 training spike (Machine B/C night, Oct 2024) ────────────
    # Single 6% probability gate — same mask drives feed spike, vibration spike,
    # AND FAIL_GOUGE in lab_testing (no second roll downstream).
    anom03_op   = idx["operator_id"].values == "OP-007"
    anom03_mach = (machine_ids == "Machine_B") | (machine_ids == "Machine_C")
    anom03_win  = (idx["day_ord"].values >= A3_LO) & (idx["day_ord"].values <= A3_HI)
    anom03_roll = RNG.random(n) <= 0.06
    anom03_mask = anom03_op & anom03_mach & anom03_win & anom03_roll
    # Feed rate spike
    feed = np.where(anom03_mask, np.round(nominal_feed * 1.20, 1), feed)
    # Vibration spike U(1.8, 2.8)
    vibration = np.where(anom03_mask, RNG.uniform(1.8, 2.8, n), vibration)
    vibration  = np.round(vibration, 4)

    return pd.DataFrame({
        "part_serial_number":    idx["serial"],
        "timestamp":             idx["timestamp"],
        "machine_id":            machine_ids,
        "part_type":             part_types,
        "spindle_speed_rpm":     spindle,
        "feed_rate_mm_min":      feed,
        "vibration_amplitude_g": vibration,
        "tool_age_part_count":   tool_age,
        "operator_id":           idx["operator_id"],
        "part_status":           part_status,
        # carry-alongs for downstream joins
        "_machine_idx":          idx["machine_idx"],
        "_day_ord":              idx["day_ord"],
        "_anom03_mask":          anom03_mask,
        "_nominal_feed":         nominal_feed,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Generate lab_testing columns (passed parts only)
# ─────────────────────────────────────────────────────────────────────────────

def _build_lab(cnc: pd.DataFrame) -> pd.DataFrame:
    passed = cnc[cnc["part_status"] == "COMPLETED_PASSED"].copy()
    n      = len(passed)
    machines = list(MACHINE_CFG.keys())

    day_ord    = passed["_day_ord"].values
    machine_id = passed["machine_id"].values
    tool_age   = passed["tool_age_part_count"].values

    # ── Dimensional deviation (ANOM-01: Machine B Apr–Jun 2022) ───────────────
    dim_dev = RNG.normal(0.0, 0.02, n)
    anom01  = (machine_id == "Machine_B") & (day_ord >= A1_LO) & (day_ord <= A1_HI)
    if anom01.any():
        # t ∈ [1, 90]
        t = np.clip((day_ord[anom01] - A1_LO) + 1, 1, 90)
        delta_d = 0.01 + ((t - 1) / 89.0) * 0.24
        dim_dev[anom01] += delta_d
    dim_dev = np.round(dim_dev, 5)

    # ── Surface roughness Ra (ANOM-02: all machines Jun–Aug 2023) ─────────────
    cw      = np.where((day_ord >= A2_LO) & (day_ord <= A2_HI), 2.5, 1.0)
    ra      = 0.03 + (0.0004 * (tool_age ** 1.4)) * cw
    ra      = np.round(ra + RNG.normal(0, 0.002, n), 4)
    ra      = np.maximum(0.0, ra)

    # ── Visual inspection ──────────────────────────────────────────────────────
    visual = np.full(n, "PASS", dtype=object)

    # High vibration → crack
    crack_mask = passed["vibration_amplitude_g"].values > 2.5
    visual[crack_mask] = "FAIL_CRACK"

    # ANOM-02: scratch from high Ra (overrides crack)
    visual[ra > 0.15] = "FAIL_SCRATCH"

    # ANOM-03: gouge from new-operator event (most severe — overrides all)
    # Uses the SAME mask from CNC generation; no second probability roll.
    anom03 = passed["_anom03_mask"].values
    visual[anom03] = "FAIL_GOUGE"

    return pd.DataFrame({
        "part_serial_number":       passed["part_serial_number"].values,
        "dimensional_deviation_mm": dim_dev,
        "surface_roughness_ra":     ra,
        "visual_inspection":        visual,
        # carry-alongs
        "_machine_id":  machine_id,
        "_day_ord":     day_ord,
        "_dim_dev":     dim_dev,
        "_ra":          ra,
        "_visual":      visual,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Generate packaging_log and customer_feedback
# ─────────────────────────────────────────────────────────────────────────────

def _build_packaging_and_feedback(
        cnc: pd.DataFrame, lab: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kit one Top + one Leg + one Stand per box from the same calendar day.
    Only passed parts enter packaging.
    """
    # Merge lab metadata back onto passed parts
    passed = cnc[cnc["part_status"] == "COMPLETED_PASSED"].copy()
    passed = passed.merge(
        lab[["part_serial_number", "_machine_id", "_day_ord",
             "_dim_dev", "_ra", "_visual"]],
        on="part_serial_number", how="left"
    )

    # Group by day_idx + machine to get lists of serials per day per machine
    passed["date_str"] = pd.to_datetime(passed["timestamp"]).dt.date
    machines = list(MACHINE_CFG.keys())

    pkg_rows  = []
    fb_rows   = []
    box_cnt   = 0
    claim_cnt = 0

    # Pivot: for each day, bucket parts by machine
    by_day = passed.groupby("date_str")

    # Packaging operators cycle round-robin per day
    rng_std = np.random.default_rng(42)

    for day, grp in by_day:
        buckets = {m: grp[grp["machine_id"] == m] for m in machines}
        n_boxes = min(len(b) for b in buckets.values())
        if n_boxes == 0:
            continue

        pkg_ts  = datetime.combine(day, datetime.min.time()).replace(hour=23)
        pkg_op  = PKG_OPS[rng_std.integers(0, 3)]

        day_ord = _ord(day)

        for b in range(n_boxes):
            box_cnt += 1
            box_serial = f"BOX-{day.strftime('%Y%m%d')}-{box_cnt:05d}"

            top   = buckets["Machine_A"].iloc[b]
            leg   = buckets["Machine_B"].iloc[b]
            stand = buckets["Machine_C"].iloc[b]

            # ANOM-05: Monday morning packaging blunder (PKG-003, Nov 1–14 2025)
            is_anom05 = (
                pkg_op == "PKG-003"
                and A5_LO <= day_ord <= A5_HI
                and rng_std.random() <= 0.08
            )
            hw_kit = not is_anom05

            pkg_rows.append({
                "box_serial_number":   box_serial,
                "timestamp":           pkg_ts,
                "top_serial_number":   top["part_serial_number"],
                "leg_serial_number":   leg["part_serial_number"],
                "stand_serial_number": stand["part_serial_number"],
                "hardware_kit_included": hw_kit,
                "packing_operator_id": pkg_op,
            })

            # ── Customer feedback (complaint-driven) ──────────────────────────
            leg_dev    = leg["_dim_dev"]
            leg_visual = leg["_visual"]
            top_visual = top["_visual"]

            fb_cat = None
            if is_anom05:
                fb_cat = "Missing Hardware"
            elif leg_dev > 0.15:
                fb_cat = "Fitment Issue"
            elif (leg_visual == "FAIL_SCRATCH" or top_visual == "FAIL_SCRATCH") \
                    and rng_std.random() < 0.03:
                fb_cat = "Surface Finish"
            elif (leg_visual == "FAIL_GOUGE" or stand["_visual"] == "FAIL_GOUGE") \
                    and rng_std.random() < 0.08:
                fb_cat = "Surface Finish"
            elif rng_std.random() < 0.003:
                fb_cat = "None"

            if fb_cat is not None:
                claim_cnt += 1
                fb_rows.append({
                    "claim_id":              f"CLM-{claim_cnt:07d}",
                    "box_serial_number":     box_serial,
                    "months_since_delivery": int(rng_std.integers(1, 25)),
                    "feedback_category":     fb_cat,
                    "customer_text":         _feedback_text(
                        fb_cat, leg_dev, leg_visual, is_anom05, rng_std),
                })

    return pd.DataFrame(pkg_rows), pd.DataFrame(fb_rows)


_ANOM01_TEXTS = [
    "The table rocks back and forth no matter how we level it.",
    "Legs are uneven when assembling — one side sits noticeably higher.",
    "Table wobbles constantly, very frustrating with a premium product.",
    "After assembly the table is unstable and rocks on a flat surface.",
]
_ANOM02_TEXTS = [
    "Visible swirly scratch marks on the finish under any light.",
    "Stainless top lacks a mirror shine — looks dull and scuffed.",
    "Surface has circular scratches that look like machine marks.",
    "The finish quality is unacceptable, deep swirl marks visible.",
]
_ANOM03_TEXTS = [
    "Deep gouge marks on the leg surface, clearly a manufacturing defect.",
    "One leg has visible tool marks gouged into the metal.",
    "Surface damage on the stand — looks like it was hit during machining.",
]
_GENERIC_TEXTS = [
    "Minor surface blemish on underside, otherwise excellent.",
    "Slight discoloration near weld point but acceptable.",
    "Assembly instructions unclear but product quality is good.",
]


def _feedback_text(cat: str, dim_dev: float, visual: str,
                   is_anom05: bool, rng) -> str:
    if is_anom05:
        return "Arrived box with no screws or wrench."
    if cat == "Fitment Issue":
        return _ANOM01_TEXTS[rng.integers(0, len(_ANOM01_TEXTS))]
    if cat == "Surface Finish":
        if visual == "FAIL_GOUGE":
            return _ANOM03_TEXTS[rng.integers(0, len(_ANOM03_TEXTS))]
        return _ANOM02_TEXTS[rng.integers(0, len(_ANOM02_TEXTS))]
    return _GENERIC_TEXTS[rng.integers(0, len(_GENERIC_TEXTS))]


# ─────────────────────────────────────────────────────────────────────────────
# Schema + write
# ─────────────────────────────────────────────────────────────────────────────

def _write_db(con: duckdb.DuckDBPyConnection,
              cnc: pd.DataFrame, lab: pd.DataFrame,
              pkg: pd.DataFrame, fb: pd.DataFrame) -> None:
    # Strip carry-along columns before writing
    cnc_cols = ["part_serial_number", "timestamp", "machine_id", "part_type",
                 "spindle_speed_rpm", "feed_rate_mm_min", "vibration_amplitude_g",
                 "tool_age_part_count", "operator_id", "part_status"]
    lab_cols = ["part_serial_number", "dimensional_deviation_mm",
                "surface_roughness_ra", "visual_inspection"]

    for tbl in ("customer_feedback", "packaging_log", "lab_testing", "cnc_telemetry"):
        con.execute(f"DROP TABLE IF EXISTS {tbl}")

    con.register("_cnc_df", cnc[cnc_cols])
    con.register("_lab_df", lab[lab_cols])
    con.register("_pkg_df", pkg)
    con.register("_fb_df",  fb)

    con.execute("CREATE TABLE cnc_telemetry      AS SELECT * FROM _cnc_df")
    con.execute("CREATE TABLE lab_testing        AS SELECT * FROM _lab_df")
    con.execute("CREATE TABLE packaging_log      AS SELECT * FROM _pkg_df")
    con.execute("CREATE TABLE customer_feedback  AS SELECT * FROM _fb_df")

    # Add primary/foreign key constraints after load (DuckDB style)
    con.execute("ALTER TABLE cnc_telemetry ADD PRIMARY KEY (part_serial_number)")
    con.execute("ALTER TABLE lab_testing   ADD PRIMARY KEY (part_serial_number)")
    con.execute("ALTER TABLE packaging_log ADD PRIMARY KEY (box_serial_number)")
    con.execute("ALTER TABLE customer_feedback ADD PRIMARY KEY (claim_id)")


# ─────────────────────────────────────────────────────────────────────────────
# Verification report
# ─────────────────────────────────────────────────────────────────────────────

def verify(db_path: str = DB_PATH) -> None:
    con = duckdb.connect(db_path, read_only=True)

    print("\n── Row counts ──────────────────────────────────────────────────")
    for tbl in ("cnc_telemetry", "lab_testing", "packaging_log", "customer_feedback"):
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:<28} {n:>10,}")

    print("\n── ANOM-01: Machine B dimensional drift Apr–Jun 2022 ───────────")
    r = con.execute("""
        SELECT
            DATE_TRUNC('month', timestamp)::DATE AS mo,
            ROUND(AVG(l.dimensional_deviation_mm), 4) AS avg_dev,
            COUNT(*) AS parts
        FROM cnc_telemetry c
        JOIN lab_testing l USING (part_serial_number)
        WHERE c.machine_id = 'Machine_B'
          AND timestamp BETWEEN '2022-03-01' AND '2022-07-31'
        GROUP BY 1 ORDER BY 1
    """).fetchall()
    for row in r:
        print(f"  {row}")

    print("\n── ANOM-02: surface roughness Jun–Aug 2023 vs baseline ─────────")
    r = con.execute("""
        SELECT
            CASE WHEN timestamp BETWEEN '2023-06-01' AND '2023-08-31'
                 THEN 'anomaly' ELSE 'baseline' END AS period,
            ROUND(AVG(l.surface_roughness_ra), 4) AS avg_ra,
            ROUND(MAX(l.surface_roughness_ra), 4) AS max_ra,
            COUNT(*) AS parts
        FROM cnc_telemetry c
        JOIN lab_testing l USING (part_serial_number)
        GROUP BY 1
    """).fetchall()
    for row in r:
        print(f"  {row}")

    print("\n── ANOM-03: OP-007 FAIL_GOUGE Oct 2024 ────────────────────────")
    r = con.execute("""
        SELECT visual_inspection, COUNT(*) AS cnt
        FROM cnc_telemetry c
        JOIN lab_testing l USING (part_serial_number)
        WHERE c.operator_id = 'OP-007'
          AND timestamp BETWEEN '2024-10-01' AND '2024-10-31'
        GROUP BY 1
    """).fetchall()
    for row in r:
        print(f"  {row}")

    print("\n── ANOM-04: rejection rate all time ────────────────────────────")
    r = con.execute("""
        SELECT part_status, COUNT(*) AS cnt
        FROM cnc_telemetry
        GROUP BY 1
    """).fetchall()
    for row in r:
        print(f"  {row}")

    print("\n── ANOM-05: Missing Hardware Nov 2025 ──────────────────────────")
    r = con.execute("""
        SELECT cf.feedback_category, COUNT(*) AS cnt
        FROM customer_feedback cf
        JOIN packaging_log p USING (box_serial_number)
        WHERE p.timestamp BETWEEN '2025-11-01' AND '2025-11-14'
        GROUP BY 1
    """).fetchall()
    for row in r:
        print(f"  {row}")

    print("\n── Customer feedback totals ─────────────────────────────────────")
    r = con.execute("""
        SELECT feedback_category, COUNT(*) AS cnt
        FROM customer_feedback
        GROUP BY 1 ORDER BY cnt DESC
    """).fetchall()
    for row in r:
        print(f"  {row}")

    con.close()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def generate(db_path: str = DB_PATH) -> None:
    import time
    t0 = time.time()

    print("Step 1/5  Building scheduling index ...")
    idx = _build_index()
    print(f"          {len(idx):,} rows indexed in {time.time()-t0:.1f}s")

    t1 = time.time()
    print("Step 2/5  Generating CNC telemetry ...")
    cnc = _build_cnc(idx)
    passed_pct = (cnc["part_status"] == "COMPLETED_PASSED").mean() * 100
    print(f"          {len(cnc):,} rows | {passed_pct:.1f}% passed  [{time.time()-t1:.1f}s]")

    t2 = time.time()
    print("Step 3/5  Generating lab testing ...")
    lab = _build_lab(cnc)
    print(f"          {len(lab):,} rows  [{time.time()-t2:.1f}s]")

    t3 = time.time()
    print("Step 4/5  Generating packaging + feedback ...")
    pkg, fb = _build_packaging_and_feedback(cnc, lab)
    print(f"          {len(pkg):,} boxes | {len(fb):,} feedback rows  [{time.time()-t3:.1f}s]")

    t4 = time.time()
    print(f"Step 5/5  Writing to {db_path} ...")
    con = duckdb.connect(db_path)
    _write_db(con, cnc, lab, pkg, fb)
    con.close()
    print(f"          Done  [{time.time()-t4:.1f}s]")

    print(f"\nTotal generation time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    generate()
    verify()
