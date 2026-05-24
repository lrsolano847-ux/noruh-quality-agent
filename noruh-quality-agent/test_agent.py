"""
Live agent integration test using the mock Ollama server.

Starts mock_ollama_server on localhost:11434, then runs NoruhAgent against
each of the 5 injected anomaly scenarios and validates:
  - The agent loop completes without errors
  - Real SQL executes against the 1.5M-row DuckDB database
  - ChromaDB semantic search runs against embedded feedback corpus
  - The Ishikawa output correctly names the expected anomaly

Run with:  python test_agent.py
"""

from __future__ import annotations

import sys
import time
import textwrap

import mock_ollama_server as mock_server
from database import NoruhDB
from agent import NoruhAgent, IshikawaAnalysis

# ── ANSI colours ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}PASS{RESET}"
FAIL = f"{RED}FAIL{RESET}"


# ── Test scenarios ────────────────────────────────────────────────────────────
TESTS = [
    {
        "name":           "ANOM-01 — Machine B Calibration Drift",
        "question":       "Why did fitment complaints spike in Q2 2022? Investigate the root cause.",
        "expected_anom":  "ANOM-01",
        "expected_cats":  ["machine"],   # at least one root cause in Machine category
    },
    {
        "name":           "ANOM-02 — Cheap Tooling Campaign",
        "question":       "Investigate the surface finish scratch complaints from summer 2023.",
        "expected_anom":  "ANOM-02",
        "expected_cats":  ["material"],
    },
    {
        "name":           "ANOM-03 — New Operator Training Spike",
        "question":       "What caused the gouge defects on Machine B in October 2024?",
        "expected_anom":  "ANOM-03",
        "expected_cats":  ["human_environment"],
    },
    {
        "name":           "ANOM-04 — Inline Tool Breakage Scrap",
        "question":       "Analyse the part rejection and inline scrap pattern across all 5 years.",
        "expected_anom":  "ANOM-04",
        "expected_cats":  ["machine", "material"],
    },
    {
        "name":           "ANOM-05 — Packaging Hardware Blunder",
        "question":       "Investigate the missing hardware screws complaints from November 2025.",
        "expected_anom":  "ANOM-05",
        "expected_cats":  ["human_environment", "method"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hdr(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 62}{RESET}")
    print(f"{BOLD}{CYAN}{text}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 62}{RESET}")


def _section(text: str) -> None:
    print(f"\n{YELLOW}{text}{RESET}")


def _indent(text: str, width: int = 4) -> str:
    return textwrap.indent(str(text), " " * width)


def _validate(result: IshikawaAnalysis, expected_anom: str,
               expected_cats: list[str]) -> list[str]:
    """Return list of failure strings (empty = all passed)."""
    failures = []

    if expected_anom not in result.anomalies_found:
        failures.append(
            f"Expected anomaly '{expected_anom}' not in anomalies_found: "
            f"{result.anomalies_found}"
        )

    for cat in expected_cats:
        items = getattr(result, cat, [])
        if not items:
            failures.append(f"Category '{cat}' is empty — expected at least one root cause")

    if not result.summary:
        failures.append("summary field is empty")

    return failures


def _print_ishikawa(result: IshikawaAnalysis) -> None:
    cats = [
        ("machine",           "⚙️  Machine"),
        ("material",          "🪛  Material"),
        ("method",            "📋  Method"),
        ("human_environment", "👤  Human/Environment"),
    ]
    print()
    for attr, label in cats:
        items = getattr(result, attr, [])
        if items:
            print(f"  {label}:")
            for item in items:
                print(_indent(f"• {item}", 6))
    if result.summary:
        print(f"\n  📝  Summary:")
        print(_indent(textwrap.fill(result.summary, width=72), 6))
    if result.anomalies_found:
        print(f"\n  🏷️   Anomalies identified: {', '.join(result.anomalies_found)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main test loop
# ─────────────────────────────────────────────────────────────────────────────

def run_tests() -> None:
    _hdr("Noruh Quality Agent — Integration Test Suite")
    print("Initialising …")

    # Start mock server
    mock_server.start(port=11434)
    time.sleep(0.3)   # let server bind

    # Load DB (vector store build included)
    print("Loading NoruhDB …")
    db = NoruhDB()
    db.build_vector_store()

    # Build agent
    print("Building NoruhAgent …")
    agent = NoruhAgent(db)

    results = {"pass": 0, "fail": 0}

    for i, test in enumerate(TESTS, 1):
        _hdr(f"Test {i}/{len(TESTS)}: {test['name']}")
        print(f"  Question: {BOLD}{test['question']}{RESET}\n")

        t0 = time.time()

        # Stream events so we can show progress
        tool_calls_made = []
        final_result    = None

        for event in agent.stream(test["question"]):
            etype = event.get("type")

            if etype == "tool_call":
                tool  = event["tool"]
                args  = event["args"]
                label = args.get("sql", args.get("query", ""))[:80]
                print(f"  → {CYAN}tool_call{RESET}  {tool}({label!r})")
                tool_calls_made.append(tool)

            elif etype == "tool_result":
                tool    = event["tool"]
                preview = event["content"]
                # Try to parse and count rows
                import json
                try:
                    rows = json.loads(preview)
                    count = len(rows) if isinstance(rows, list) else "?"
                    print(f"  ← {GREEN}result{RESET}     {tool} → {count} rows")
                except Exception:
                    print(f"  ← {GREEN}result{RESET}     {tool} → {preview[:60]}")

            elif etype == "critic":
                content = event.get("content", "")
                verdict = "SUFFICIENT" if ("SUFFICIENT" in content and
                           "INSUFFICIENT" not in content) else "INSUFFICIENT"
                icon    = "✅" if verdict == "SUFFICIENT" else "🔄"
                retry   = event.get("retry", "?")
                print(f"  🔍 {YELLOW}critic{RESET}     pass {retry} — {icon} {verdict}")

            elif etype == "final":
                raw = event.get("content", {})
                try:
                    final_result = IshikawaAnalysis(**raw)
                except Exception as exc:
                    print(f"  {RED}Failed to parse Ishikawa output: {exc}{RESET}")

        elapsed = time.time() - t0

        if final_result is None:
            print(f"\n  {FAIL}  No Ishikawa result returned")
            results["fail"] += 1
            continue

        # Print the full Ishikawa output
        _section("  Ishikawa Root-Cause Analysis:")
        _print_ishikawa(final_result)

        # Validate
        failures = _validate(final_result, test["expected_anom"], test["expected_cats"])

        print(f"\n  Tools used: {', '.join(tool_calls_made) or 'none'}")
        print(f"  Elapsed:    {elapsed:.1f}s")

        if failures:
            print(f"\n  Status: {FAIL}")
            for f in failures:
                print(f"    ✗ {f}")
            results["fail"] += 1
        else:
            print(f"\n  Status: {PASS}")
            results["pass"] += 1

    # Summary
    _hdr("Test Summary")
    total = results["pass"] + results["fail"]
    colour = GREEN if results["fail"] == 0 else RED
    print(f"  {colour}{BOLD}{results['pass']}/{total} passed{RESET}")
    if results["fail"] > 0:
        print(f"  {RED}{results['fail']} failed{RESET}")

    mock_server.stop()
    sys.exit(0 if results["fail"] == 0 else 1)


if __name__ == "__main__":
    run_tests()
