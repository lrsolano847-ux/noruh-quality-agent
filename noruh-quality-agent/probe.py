"""
Live prompt validation probe for Noruh Quality Agent.

Run this BEFORE the full app to cheaply check that both models understand
their output contracts.  Requires Ollama to be running with both models pulled.

Usage:
    python probe.py                     # tests both models
    python probe.py --model tool        # tests qwen3-coder:7b only
    python probe.py --model critic      # tests deepseek-r1:8b only
    python probe.py --verbose           # print full raw model responses
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import urllib.error
import urllib.request

OLLAMA_URL   = "http://localhost:11434"
TOOL_MODEL   = "qwen2.5-coder:7b"
CRITIC_MODEL = "qwen2.5-coder:7b"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _ollama_chat(model: str, messages: list[dict], timeout: int = 90) -> str:
    payload = json.dumps({
        "model":    model,
        "messages": messages,
        "stream":   False,
        "options":  {"temperature": 0.1},
        "keep_alive": 0,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())["message"]["content"]


def _extract_tag(text: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_ishikawa(text: str) -> tuple[bool, str]:
    """Returns (ok, diagnosis)."""
    raw = _extract_tag(text, "ishikawa")
    if raw is None:
        return False, "No <ishikawa> block found in response"

    # Strip code fences
    raw = re.sub(r"```(?:json)?\s*\n?", "", raw).replace("```", "").strip()
    brace = raw.find("{")
    if brace > 0:
        raw = raw[brace:]
    rbrace = raw.rfind("}")
    if rbrace >= 0:
        raw = raw[:rbrace + 1]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
        cleaned = re.sub(r"\bTrue\b",  "true",  cleaned)
        cleaned = re.sub(r"\bFalse\b", "false", cleaned)
        cleaned = re.sub(r"\bNone\b",  "null",  cleaned)
        try:
            parsed = json.loads(cleaned)
        except Exception as exc:
            return False, f"JSON parse failed after lenient cleanup: {exc}\nExtracted:\n{raw[:500]}"

    required = {"machine", "material", "method", "human_environment", "summary", "anomalies_found"}
    missing  = required - set(parsed.keys())
    if missing:
        return False, f"JSON valid but missing keys: {missing}"

    return True, f"OK — keys present, anomalies_found={parsed.get('anomalies_found')}"


def _check_ollama() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            data   = json.loads(resp.read())
            names  = [m["name"] for m in data.get("models", [])]
            needed = [TOOL_MODEL, CRITIC_MODEL]
            missing = [m for m in needed if m not in names]
            if missing:
                print(f"[ERROR] Ollama running but models not pulled: {missing}")
                print(f"        Run: ollama pull {' && ollama pull '.join(missing)}")
                return False
            return True
    except urllib.error.URLError as exc:
        print(f"[ERROR] Ollama not reachable at {OLLAMA_URL}: {exc}")
        print("        Start it with: ollama serve")
        return False


# ── Probe 1: Tool-calling model — <ishikawa> format ──────────────────────────

TOOL_PROBE_PROMPT = textwrap.dedent("""
    You are a manufacturing data analyst for Noruh Manufacturing.

    A customer reported that tables from April–June 2022 wobble on flat surfaces.
    Assume you have already run SQL queries and found that Machine B's dimensional
    deviation increased from 0.01 mm in April to 0.25 mm in June 2022.

    Write a brief analysis (2–3 sentences), then output exactly this JSON block:

    <ishikawa>
    {
      "machine":           ["Machine B calibration drift Apr–Jun 2022"],
      "material":          [],
      "method":            ["No SPC alerting configured for dimensional drift"],
      "human_environment": [],
      "summary":           "Machine B drifted progressively over 90 days, causing fitment issues.",
      "anomalies_found":   ["ANOM-01"]
    }
    </ishikawa>

    Use the exact format above for YOUR response. Fill in realistic details.
""").strip()


def probe_tool_model(verbose: bool = False) -> bool:
    print(f"\n{'─'*60}")
    print(f"PROBE 1 — {TOOL_MODEL}: <ishikawa> format")
    print(f"{'─'*60}")
    print("  Sending minimal prompt with worked example …")
    try:
        response = _ollama_chat(TOOL_MODEL, [{"role": "user", "content": TOOL_PROBE_PROMPT}])
    except Exception as exc:
        print(f"  [FAIL] Request error: {exc}")
        return False

    if verbose:
        print(f"\n  Raw response:\n{textwrap.indent(response, '  ')}\n")

    ok, diagnosis = _parse_ishikawa(response)
    icon = "✅" if ok else "❌"
    print(f"  {icon} Ishikawa parse: {diagnosis}")

    # Check for code fences (informational — we handle them but want to know)
    if "```" in (_extract_tag(response, "ishikawa") or ""):
        print("  ⚠️  NOTE: Model wrapped JSON in code fences (handled, but consider "
              "reinforcing the prompt to avoid them)")

    # Check for thinking tokens
    if "<think>" in response:
        think_len = len(_extract_tag(response, "think") or "")
        print(f"  ℹ️  Model emitted a <think> block ({think_len} chars) — "
              "this is normal for qwen3 and does not affect parsing")

    return ok


# ── Probe 2: Critic model — <verdict> format ─────────────────────────────────

CRITIC_PROBE_PROMPT = textwrap.dedent("""
    You are reviewing a manufacturing root-cause investigation.

    The agent ran these queries and found:
    - Monthly avg dimensional deviation on Machine B rose from 0.01 mm (Jan 2022)
      to 0.25 mm (Jun 2022) — a clear 6-month drift.
    - The anomaly is attributed to Machine B specifically (not Machine A or C).
    - Customer feedback confirms "rocking table" and "wobbly legs" complaints
      cluster in the same period.
    - The Ishikawa block contains specific causes in Machine and Method categories.

    Decide if this is SUFFICIENT or INSUFFICIENT evidence.

    Respond using EXACTLY this format:

    When sufficient:
    <verdict>SUFFICIENT</verdict>
    <critique>
    Evidence is complete. [One sentence why.]
    </critique>

    When insufficient:
    <verdict>INSUFFICIENT</verdict>
    <critique>
    Missing: [What is missing.]
    </critique>
""").strip()


def probe_critic_model(verbose: bool = False) -> bool:
    print(f"\n{'─'*60}")
    print(f"PROBE 2 — {CRITIC_MODEL}: <verdict> format")
    print(f"{'─'*60}")
    print("  Sending minimal prompt with clear evidence …")
    try:
        response = _ollama_chat(CRITIC_MODEL, [{"role": "user", "content": CRITIC_PROBE_PROMPT}])
    except Exception as exc:
        print(f"  [FAIL] Request error: {exc}")
        return False

    if verbose:
        print(f"\n  Raw response:\n{textwrap.indent(response, '  ')}\n")

    verdict  = _extract_tag(response, "verdict")
    critique = _extract_tag(response, "critique")
    think    = _extract_tag(response, "think")

    if think:
        print(f"  ℹ️  Model emitted a <think> block ({len(think)} chars)")

    if verdict is None:
        print("  ❌ No <verdict> tag found — agent will default to INSUFFICIENT on every pass")
        print(f"     Response preview: {response[:300]!r}")
        return False

    verdict_norm = verdict.strip().upper()
    print(f"  ✅ <verdict> tag found: {verdict_norm!r}")

    if critique is None:
        print("  ⚠️  No <critique> tag found — agent will use raw response text as critique")
    else:
        print(f"  ✅ <critique> tag found ({len(critique)} chars)")

    if verdict_norm == "SUFFICIENT":
        print("  ✅ Correctly identified evidence as SUFFICIENT")
        return True
    else:
        print(f"  ⚠️  Model returned {verdict_norm!r} despite strong evidence — "
              "may cause extra retry passes in production")
        print(f"     Critique: {(critique or '')[:200]}")
        return False


# ── Probe 3: Retry routing — does INSUFFICIENT critique actually guide the model? ─

RETRY_PROBE_PROMPT_1 = textwrap.dedent("""
    You are a manufacturing data analyst. A root-cause investigation found elevated
    defect rates in 2022 but did NOT yet link them to a specific machine.

    A senior auditor reviewed your work and said:

    [CRITIC — retry 1/3]
    Verdict: INSUFFICIENT

    Critique:
    Missing: the machine-level breakdown. Run:
      SELECT machine_id, AVG(dimensional_deviation_mm) FROM lab_testing
      JOIN cnc_telemetry USING (part_serial_number)
      WHERE timestamp BETWEEN '2022-04-01' AND '2022-06-30'
      GROUP BY machine_id

    Now call the execute_sql tool with that query.
""").strip()


def probe_retry_routing(verbose: bool = False) -> bool:
    print(f"\n{'─'*60}")
    print(f"PROBE 3 — {TOOL_MODEL}: follows INSUFFICIENT critique with a tool call")
    print(f"{'─'*60}")
    print("  Sending INSUFFICIENT critique, expecting a tool call …")

    tool_schema = {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Run a SQL query against the manufacturing database.",
            "parameters": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
        },
    }

    payload = json.dumps({
        "model":    TOOL_MODEL,
        "messages": [{"role": "user", "content": RETRY_PROBE_PROMPT_1}],
        "tools":    [tool_schema],
        "stream":   False,
        "options":  {"temperature": 0.1},
        "keep_alive": 0,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"  [FAIL] Request error: {exc}")
        return False

    msg        = data.get("message", {})
    tool_calls = msg.get("tool_calls", [])
    content    = msg.get("content", "")

    if verbose:
        print(f"\n  Raw message: {json.dumps(msg, indent=2)[:800]}\n")

    if tool_calls:
        tc   = tool_calls[0]
        name = tc.get("function", {}).get("name", "?")
        args = tc.get("function", {}).get("arguments", {})
        print(f"  ✅ Tool call issued: {name}({json.dumps(args)[:120]})")
        return True
    elif "<ishikawa>" in content:
        print("  ⚠️  Model jumped straight to <ishikawa> without running the recommended query")
        print("     This may cause incomplete analyses when the critic requests more data")
        return False
    else:
        print("  ❌ No tool call and no <ishikawa> — model produced plain text")
        print(f"     Preview: {content[:300]!r}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Ollama models for prompt compliance")
    parser.add_argument("--model",   choices=["tool", "critic", "both"], default="both")
    parser.add_argument("--verbose", action="store_true",
                        help="Print full raw model responses")
    args = parser.parse_args()

    print("Noruh Quality Agent — Live Prompt Validation Probe")
    print("=" * 60)

    if not _check_ollama():
        sys.exit(1)

    results: dict[str, bool] = {}

    if args.model in ("tool", "both"):
        results["tool_ishikawa_format"] = probe_tool_model(verbose=args.verbose)
        results["tool_retry_routing"]   = probe_retry_routing(verbose=args.verbose)

    if args.model in ("critic", "both"):
        results["critic_verdict_format"] = probe_critic_model(verbose=args.verbose)

    print(f"\n{'─'*60}")
    print("SUMMARY")
    print(f"{'─'*60}")
    all_pass = True
    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name}")
        if not ok:
            all_pass = False

    if all_pass:
        print("\n  All probes passed — models are following prompt contracts.")
        print("  You can now run: streamlit run app.py")
    else:
        print("\n  Some probes failed. See CLAUDE.md section 1 for tuning guidance.")
        print("  Re-run with --verbose to see full model responses.")
    print()


if __name__ == "__main__":
    main()
