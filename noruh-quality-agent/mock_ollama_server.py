"""
Mock Ollama server for testing the Noruh quality agent without real LLM models.

Listens on localhost:11434 (same address the agent uses) and responds to:
  GET  /api/tags   — reports qwen3-coder:7b and deepseek-r1:8b as available
  POST /api/chat   — returns scripted diagnostic responses with real SQL queries

The server is stateless: it infers (a) which anomaly scenario is being
investigated from keyword matching on the user's question, and (b) which step
of the 3-step flow to execute by counting tool-result messages already in the
conversation history.

This means the agent's tool_executor runs REAL SQL against the REAL 1.5M-row
DuckDB database — only the LLM responses are mocked.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Model names (must match agent.py) ─────────────────────────────────────────
TOOL_MODEL   = "qwen3-coder:7b"
CRITIC_MODEL = "deepseek-r1:8b"


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic scenarios — one per injected anomaly
# Each scenario has:
#   keywords  : matched against the user's first question (case-insensitive)
#   sql_1     : primary SQL query (call 1 from tool-caller)
#   sql_2     : optional follow-up SQL query (call 2) — None to skip
#   search    : semantic search query (last tool call before final analysis)
#   ishikawa  : final structured root-cause JSON
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS: list[dict] = [

    # ── ANOM-01: Machine B calibration drift ─────────────────────────────────
    {
        "keywords": ["fitment", "wobbly", "wobble", "rock", "uneven", "2022", "q2"],
        "sql_1": """
SELECT
    DATE_TRUNC('month', c.timestamp)::DATE AS month,
    ROUND(AVG(l.dimensional_deviation_mm), 4)  AS avg_deviation_mm,
    ROUND(MAX(l.dimensional_deviation_mm), 4)  AS max_deviation_mm,
    COUNT(*) FILTER (WHERE l.dimensional_deviation_mm > 0.15) AS high_dev_parts,
    COUNT(*) AS total_parts
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.machine_id = 'Machine_B'
  AND c.timestamp BETWEEN '2022-01-01' AND '2022-12-31'
GROUP BY 1 ORDER BY 1
""".strip(),
        "sql_2": """
SELECT
    c.machine_id,
    ROUND(AVG(c.spindle_speed_rpm), 1)    AS avg_spindle_rpm,
    ROUND(AVG(c.vibration_amplitude_g), 3) AS avg_vibration_g,
    ROUND(AVG(l.dimensional_deviation_mm), 5) AS avg_dim_dev,
    COUNT(*) AS parts
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.timestamp BETWEEN '2022-04-01' AND '2022-06-30'
GROUP BY 1 ORDER BY avg_dim_dev DESC
""".strip(),
        "search": "table rocks wobbles uneven legs assembly fitment",
        "ishikawa": {
            "machine": [
                "Machine B (Leg fabricator) experienced progressive spindle calibration drift "
                "from April 1 to June 30, 2022",
                "Dimensional deviation increased linearly from +0.01 mm to +0.25 mm over 90 days "
                "— consistent with worn spindle bearings or a drifting fixture datum"
            ],
            "material": [],
            "method": [
                "Scheduled metrology intervals failed to catch the drift before it exceeded "
                "the 0.15 mm fitment threshold",
                "No automated SPC alert was configured to flag progressive dimensional drift trends "
                "on Machine B"
            ],
            "human_environment": [
                "Corrective maintenance was not triggered despite the linearly growing deviation "
                "signal visible in daily lab records"
            ],
            "summary": (
                "ANOM-01: Machine B (Leg fabricator) suffered a 90-day progressive calibration "
                "drift (Apr 1–Jun 30, 2022). Average dimensional deviation peaked at 0.21 mm in "
                "June — well above the 0.15 mm fitment threshold. All tables assembled with legs "
                "from this window have asymmetric leg lengths, producing the reported rocking and "
                "wobbling symptoms in 4,615 customer complaints."
            ),
            "anomalies_found": ["ANOM-01"],
        },
    },

    # ── ANOM-02: Cheap tooling campaign ──────────────────────────────────────
    {
        "keywords": ["surface", "finish", "scratch", "swirl", "2023", "summer", "tooling", "mirror"],
        "sql_1": """
SELECT
    DATE_TRUNC('month', c.timestamp)::DATE AS month,
    ROUND(AVG(l.surface_roughness_ra), 4) AS avg_ra,
    ROUND(MAX(l.surface_roughness_ra), 4) AS max_ra,
    COUNT(*) FILTER (WHERE l.visual_inspection = 'FAIL_SCRATCH') AS scratch_failures,
    COUNT(*) AS total_parts
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.timestamp BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY 1 ORDER BY 1
""".strip(),
        "sql_2": """
SELECT
    c.machine_id,
    ROUND(AVG(c.tool_age_part_count), 1) AS avg_tool_age,
    ROUND(AVG(l.surface_roughness_ra), 4) AS avg_ra,
    COUNT(*) FILTER (WHERE l.visual_inspection = 'FAIL_SCRATCH') AS scratches,
    COUNT(*) AS parts
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.timestamp BETWEEN '2023-06-01' AND '2023-08-31'
GROUP BY 1 ORDER BY avg_ra DESC
""".strip(),
        "search": "scratch swirl marks stainless finish polish mirror quality",
        "ishikawa": {
            "machine": [],
            "material": [
                "An inferior tooling batch was deployed across all three CNC machines "
                "June 1–August 31, 2023 (Cheap Tooling Campaign)",
                "Tool wear coefficient increased 2.5× (Cw = 2.5 vs normal Cw = 1.0), driving "
                "average surface roughness Ra from 0.76 μm baseline to 1.85 μm — 12× above the "
                "0.10 μm mirror-finish target"
            ],
            "method": [
                "Tooling procurement batch for June 2023 had no incoming Ra certification or "
                "trial-cut qualification before fleet deployment",
                "Tool replacement intervals were not shortened to compensate for the 2.5× faster "
                "wear rate of the inferior batch"
            ],
            "human_environment": [],
            "summary": (
                "ANOM-02: A sub-standard tooling batch was deployed fleet-wide from "
                "June–August 2023. The batch wore 2.5× faster than normal, pushing average "
                "surface roughness Ra from a 0.76 μm baseline to 1.85 μm — well above the "
                "0.15 μm scratch threshold. Parts from this window exhibit visible swirl marks "
                "on the stainless surface, generating a spike in Surface Finish customer complaints."
            ),
            "anomalies_found": ["ANOM-02"],
        },
    },

    # ── ANOM-03: New operator training spike ──────────────────────────────────
    {
        "keywords": ["gouge", "october", "2024", "operator", "op-007", "night", "training"],
        "sql_1": """
SELECT
    c.operator_id,
    c.machine_id,
    l.visual_inspection,
    ROUND(AVG(c.feed_rate_mm_min), 1)      AS avg_feed_rate_mm_min,
    ROUND(AVG(c.vibration_amplitude_g), 3) AS avg_vibration_g,
    COUNT(*) AS parts
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.timestamp BETWEEN '2024-10-01' AND '2024-10-31'
GROUP BY 1, 2, 3
ORDER BY parts DESC
LIMIT 20
""".strip(),
        "sql_2": """
SELECT
    c.operator_id,
    ROUND(AVG(c.feed_rate_mm_min), 1)       AS avg_feed,
    ROUND(AVG(c.vibration_amplitude_g), 3)  AS avg_vib,
    COUNT(*) FILTER (WHERE l.visual_inspection = 'FAIL_GOUGE')   AS gouges,
    COUNT(*) FILTER (WHERE l.visual_inspection = 'FAIL_SCRATCH') AS scratches,
    COUNT(*) AS total
FROM cnc_telemetry c
JOIN lab_testing l USING (part_serial_number)
WHERE c.machine_id IN ('Machine_B', 'Machine_C')
  AND c.timestamp BETWEEN '2024-10-01' AND '2024-10-31'
GROUP BY 1
ORDER BY gouges DESC
""".strip(),
        "search": "gouge marks tool damage operator error machining defect",
        "ishikawa": {
            "machine": [],
            "material": [],
            "method": [
                "OP-007 ran feed rates 20% above nominal (1,440 mm/min vs 1,200 mm/min on "
                "Machine B) during October 2024 night shifts",
                "Over-speed feed rates caused vibration spikes of 1.8–2.8 g, directly inducing "
                "FAIL_GOUGE defects on 76 parts — a 6% defect rate vs near-zero baseline"
            ],
            "human_environment": [
                "OP-007 was a newly onboarded operator assigned to Machine B and C night shifts "
                "in October 2024 without adequate supervised run-off",
                "No real-time feed-rate alarm was configured to alert supervisors when "
                "operator-set rates exceeded nominal by more than 10%",
                "Night shift had reduced supervision coverage, allowing the over-speed condition "
                "to persist for the entire month"
            ],
            "summary": (
                "ANOM-03: Newly trained operator OP-007, assigned to Machine B and C night "
                "shifts in October 2024, consistently ran feed rates 20% above nominal. "
                "This drove vibration into the 1.8–2.8 g range, producing 76 FAIL_GOUGE "
                "parts — a 6% defect rate within the affected operator/window combination "
                "versus near-zero baseline across all other operators."
            ),
            "anomalies_found": ["ANOM-03"],
        },
    },

    # ── ANOM-04: Continuous inline scrap mechanic ─────────────────────────────
    {
        "keywords": ["rejection", "reject", "scrap", "vibration", "tool breakage", "anom-04", "inline"],
        "sql_1": """
SELECT
    DATE_TRUNC('year', timestamp)::DATE AS year,
    machine_id,
    COUNT(*) FILTER (WHERE part_status = 'COMPLETED_REJECTED') AS rejected,
    COUNT(*) AS total,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE part_status = 'COMPLETED_REJECTED') / COUNT(*), 3
    ) AS reject_pct,
    ROUND(AVG(vibration_amplitude_g)
        FILTER (WHERE part_status = 'COMPLETED_REJECTED'), 3) AS avg_rejection_vib_g
FROM cnc_telemetry
GROUP BY 1, 2
ORDER BY 1, 2
""".strip(),
        "sql_2": """
SELECT
    tool_age_part_count / 50 * 50 AS tool_age_bucket,
    COUNT(*) FILTER (WHERE part_status = 'COMPLETED_REJECTED') AS rejected,
    COUNT(*) AS total,
    ROUND(AVG(vibration_amplitude_g), 3) AS avg_vib
FROM cnc_telemetry
GROUP BY 1
ORDER BY 1
""".strip(),
        "search": "tool breakage vibration machine rejection catastrophic failure",
        "ishikawa": {
            "machine": [
                "Catastrophic tool breakage events occur when vibration amplitude exceeds 3.5 g, "
                "triggering immediate part rejection and a forced tool change",
                "Rejection rate of ~0.19% is consistent and continuous across all 5 years and "
                "all three machines — confirming this is a designed-in inline scrap mechanism, "
                "not a specific anomaly event"
            ],
            "material": [
                "Tool degradation is the physical root cause — vibration climbs as tool_age "
                "approaches the 400-part lifecycle limit, with breakage risk spiking above "
                "tool_age 350"
            ],
            "method": [
                "The current COMPLETED_REJECTED → immediate tool swap protocol correctly "
                "isolates bad parts from the downstream quality chain",
                "No rejected parts enter lab_testing, packaging_log, or customer_feedback"
            ],
            "human_environment": [],
            "summary": (
                "ANOM-04: 1,277 parts (0.19%) were rejected across all machines over 5 years "
                "due to catastrophic tool breakage (vibration > 3.5 g). This is a controlled, "
                "continuous inline scrap mechanism — not a discrete anomaly. Each rejection "
                "resets the tool age counter. The mechanism successfully prevents defective "
                "parts from reaching customers."
            ),
            "anomalies_found": ["ANOM-04"],
        },
    },

    # ── ANOM-05: Monday morning packaging blunder ─────────────────────────────
    {
        "keywords": ["missing hardware", "missing screws", "hardware", "packaging", "november", "2025", "pkg", "wrench", "screws"],
        "sql_1": """
SELECT
    p.packing_operator_id,
    p.hardware_kit_included,
    cf.feedback_category,
    COUNT(*) AS cnt
FROM packaging_log p
JOIN customer_feedback cf USING (box_serial_number)
WHERE p.timestamp BETWEEN '2025-11-01' AND '2025-11-14'
GROUP BY 1, 2, 3
ORDER BY cnt DESC
""".strip(),
        "sql_2": """
SELECT
    p.packing_operator_id,
    COUNT(*) FILTER (WHERE NOT p.hardware_kit_included)  AS missing_kit_boxes,
    COUNT(*) AS total_boxes,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE NOT p.hardware_kit_included) / COUNT(*), 1
    ) AS missing_pct
FROM packaging_log p
WHERE p.timestamp BETWEEN '2025-11-01' AND '2025-11-14'
GROUP BY 1
ORDER BY missing_kit_boxes DESC
""".strip(),
        "search": "missing screws hardware wrench assembly kit not included",
        "ishikawa": {
            "machine": [],
            "material": [],
            "method": [
                "No end-of-line weight check or kit-presence sensor was installed at the "
                "packaging station to verify hardware inclusion before box sealing",
                "The hardware kit insertion step had no poka-yoke mechanism — a single operator "
                "decision with no automated verification"
            ],
            "human_environment": [
                "PKG-003 omitted hardware kits from approximately 8% of boxes handled during "
                "November 1–14, 2025",
                "64 customers received assembled tables with no screws or assembly wrench — "
                "representing 100% of the Missing Hardware complaint category"
            ],
            "summary": (
                "ANOM-05: Packaging operator PKG-003 failed to include hardware kits in ~8% "
                "of boxes during the two-week window of November 1–14, 2025. 64 customers "
                "received tables with no screws or assembly wrench. Root cause is the absence "
                "of a poka-yoke (weight sensor or presence check) at the packaging station, "
                "combined with single-operator accountability for the kit insertion step."
            ),
            "anomalies_found": ["ANOM-05"],
        },
    },

    # ── CATCH-ALL: general quality overview ───────────────────────────────────
    {
        "keywords": [],   # matches anything not caught above
        "sql_1": """
SELECT
    DATE_TRUNC('year', c.timestamp)::DATE AS year,
    COUNT(*) FILTER (WHERE c.part_status = 'COMPLETED_REJECTED')   AS cnc_rejected,
    COUNT(*) FILTER (WHERE l.visual_inspection != 'PASS')          AS lab_failures,
    COUNT(*) AS total_parts,
    ROUND(100.0 * COUNT(*) FILTER (WHERE l.visual_inspection != 'PASS') / COUNT(*), 2)
        AS failure_pct
FROM cnc_telemetry c
LEFT JOIN lab_testing l USING (part_serial_number)
GROUP BY 1 ORDER BY 1
""".strip(),
        "sql_2": """
SELECT
    cf.feedback_category,
    DATE_TRUNC('year', p.timestamp)::DATE AS year,
    COUNT(*) AS complaints
FROM customer_feedback cf
JOIN packaging_log p USING (box_serial_number)
GROUP BY 1, 2
ORDER BY 2, complaints DESC
""".strip(),
        "search": "quality defect manufacturing problem customer complaint",
        "ishikawa": {
            "machine": [
                "Machine B calibration drift (Apr–Jun 2022) caused 4,615 Fitment Issue complaints — ANOM-01",
                "All machines experienced 1,277 total tool-breakage rejections over 5 years — ANOM-04"
            ],
            "material": [
                "Sub-standard tooling batch deployed June–August 2023 caused 2.4× Ra spike — ANOM-02"
            ],
            "method": [
                "No SPC alerting for progressive dimensional drift (ANOM-01)",
                "No incoming tooling qualification before fleet deployment (ANOM-02)"
            ],
            "human_environment": [
                "Undertrained operator OP-007 over-sped feed rates in October 2024, causing 76 FAIL_GOUGE parts — ANOM-03",
                "PKG-003 omitted hardware kits from 8% of boxes in November 2025 — ANOM-05"
            ],
            "summary": (
                "Full 5-year quality audit identified all five injected anomalies: "
                "ANOM-01 (Machine B calibration drift 2022), ANOM-02 (Cheap tooling 2023), "
                "ANOM-03 (New operator gouges Oct 2024), ANOM-04 (Continuous inline tool-breakage scrap), "
                "ANOM-05 (PKG-003 missing hardware Nov 2025). "
                "Fitment Issues and Surface Finish complaints are the dominant customer-facing categories."
            ),
            "anomalies_found": ["ANOM-01", "ANOM-02", "ANOM-03", "ANOM-04", "ANOM-05"],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Scenario matching
# ─────────────────────────────────────────────────────────────────────────────

def _match_scenario(messages: list[dict]) -> dict:
    """Pick the scenario whose keywords best match the user's question."""
    question = ""
    for m in messages:
        if m.get("role") == "user":
            question = m.get("content", "").lower()
            break

    best, best_hits = SCENARIOS[-1], 0   # catch-all default
    for s in SCENARIOS[:-1]:
        hits = sum(1 for kw in s["keywords"] if kw in question)
        if hits > best_hits:
            best, best_hits = s, hits
    return best


def _count_tool_results(messages: list[dict]) -> int:
    """Count how many tool-result messages are already in the conversation."""
    return sum(1 for m in messages if m.get("role") == "tool")


# ─────────────────────────────────────────────────────────────────────────────
# Response builders
# ─────────────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def _base_response(model: str) -> dict:
    return {
        "model": model,
        "created_at": _ts(),
        "done": True,
        "done_reason": "stop",
        "total_duration":      500_000_000,
        "load_duration":               0,
        "prompt_eval_count":         128,
        "prompt_eval_duration": 200_000_000,
        "eval_count":                 64,
        "eval_duration":        300_000_000,
    }


def _tool_call_response(model: str, tool_name: str, args: dict) -> dict:
    r = _base_response(model)
    r["message"] = {
        "role":    "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": tool_name, "arguments": args}}],
    }
    return r


def _text_response(model: str, content: str) -> dict:
    r = _base_response(model)
    r["message"] = {"role": "assistant", "content": content}
    return r


def _build_ishikawa_text(ishikawa: dict) -> str:
    return (
        "Based on the SQL evidence and semantic search results, I have identified the "
        "root cause and classified it using the Ishikawa fishbone framework.\n\n"
        "<ishikawa>\n"
        + json.dumps(ishikawa, indent=2)
        + "\n</ishikawa>"
    )


def _critic_response(model: str) -> dict:
    content = (
        "<think>\n"
        "The tool-calling agent has gathered SQL aggregation data showing clear statistical "
        "anomaly patterns, and the semantic search confirms the customer complaint language "
        "matches the identified manufacturing defect. The Ishikawa categories are well-populated "
        "with specific, actionable root causes. The evidence chain from process parameter → "
        "lab defect → customer complaint is complete and traceable.\n"
        "</think>\n\n"
        "<verdict>SUFFICIENT</verdict>\n"
        "<critique>\n"
        "The investigation is complete. The SQL data provides unambiguous statistical evidence "
        "of the anomaly window and magnitude. The semantic search validates that customer "
        "complaint language matches the identified defect type. The Ishikawa categorisation "
        "correctly maps root causes to the appropriate fishbone branches with specific, "
        "actionable detail. No further queries are required.\n"
        "</critique>"
    )
    return _text_response(model, content)


# ─────────────────────────────────────────────────────────────────────────────
# Request handler
# ─────────────────────────────────────────────────────────────────────────────

class OllamaMockHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  [mock] {self.address_string()} — {fmt % args}")

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send_json({
                "models": [
                    {"name": TOOL_MODEL,   "model": TOOL_MODEL,
                     "size": 4_700_000_000, "digest": "mock-tool"},
                    {"name": CRITIC_MODEL, "model": CRITIC_MODEL,
                     "size": 4_900_000_000, "digest": "mock-critic"},
                ]
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        model    = payload.get("model", "")
        messages = payload.get("messages", [])

        if self.path == "/api/chat":
            response = self._handle_chat(model, messages)
            self._send_json(response)
        else:
            self._send_json({"error": "not found"}, 404)

    def _handle_chat(self, model: str, messages: list[dict]) -> dict:
        scenario      = _match_scenario(messages)
        tool_results  = _count_tool_results(messages)

        # ── Critic model: always approve ──────────────────────────────────────
        if CRITIC_MODEL in model:
            return _critic_response(model)

        # ── Tool-calling model: 3-step flow ───────────────────────────────────
        # Step 0: primary SQL query
        if tool_results == 0:
            return _tool_call_response(model, "execute_sql", {"sql": scenario["sql_1"]})

        # Step 1: follow-up SQL or semantic search
        if tool_results == 1:
            if scenario.get("sql_2"):
                return _tool_call_response(model, "execute_sql", {"sql": scenario["sql_2"]})
            else:
                return _tool_call_response(model, "semantic_search",
                                           {"query": scenario["search"], "n_results": 8})

        # Step 2: semantic search (if sql_2 was used in step 1)
        if tool_results == 2 and scenario.get("sql_2"):
            return _tool_call_response(model, "semantic_search",
                                       {"query": scenario["search"], "n_results": 8})

        # Final step: return analysis + Ishikawa JSON
        return _text_response(model, _build_ishikawa_text(scenario["ishikawa"]))


# ─────────────────────────────────────────────────────────────────────────────
# Server lifecycle
# ─────────────────────────────────────────────────────────────────────────────

_server: HTTPServer | None = None
_thread: threading.Thread | None = None


def start(port: int = 11434) -> None:
    global _server, _thread
    _server = HTTPServer(("127.0.0.1", port), OllamaMockHandler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()
    print(f"Mock Ollama server started on http://127.0.0.1:{port}")


def stop() -> None:
    if _server:
        _server.shutdown()
        print("Mock Ollama server stopped.")


if __name__ == "__main__":
    start()
    print("Press Ctrl+C to stop.")
    try:
        _thread.join()
    except KeyboardInterrupt:
        stop()
