"""CLI cross-check, comparison + report (Forge spec §7.5).

Diffs the TS and Python artifacts and writes `crosscheck/report.md`. Exit code 1 if any
BLOCKING divergence is found, so this can gate the M5 sign-off.

Checks, in descending order of what they prove:

  1. PROMPT PARITY (blocking) — the system + user strings must be byte-identical. This is the
     lineage guarantee: same strings, same cache key, same published behaviour. Nothing else
     matters if this fails.
  2. PARSE PARITY (blocking) — both parsers, over the same raw response, must extract the
     same `resolved` indices/texts and the same `drop` set.
  3. GUARDRAIL PARITY (blocking) — the diff gate must return the same verdict per edit.
  4. EXPECTED DIVERGENCES (reported, not blocking) — the places the two are different BY
     DESIGN, listed explicitly so a reader can see they were considered rather than missed:
       * heading blocks: the CLI skips `#`-leading sentences for reference resolution; ADF
         headings arrive as ordinary blocks and are eligible here
       * blocked edits: the CLI discards them silently; the app displays them as `blocked`
       * segmentation: sentences (CLI) vs ADF blocks (app) — neutralised by this harness,
         which feeds both the same blocks, and therefore NOT measured here
  5. MODEL AGREEMENT (informational) — only with `--live` on the Python side: whether the
     model returned the same answer twice at temperature 0. Noise, not drift.

Usage:
    python scripts/crosscheck_compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CROSSCHECK = REPO / "crosscheck"

# The report is written UTF-8, but a Windows console defaults to cp1252 and would raise on
# the arrows/em-dashes when echoing it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def norm_resolved(items: list[dict]) -> dict[int, str]:
    return {r["i"]: r.get("text", "") for r in items if isinstance(r.get("i"), int)}


def compare_page(ts: dict, py: dict) -> dict:
    blocking: list[str] = []
    expected: list[str] = []

    if ts["system"] != py["system"]:
        blocking.append("system prompt differs")
    if ts["prompt"] != py["prompt"]:
        blocking.append("user prompt differs")
    if ts.get("subject") != py.get("subject"):
        blocking.append(f"subject differs: TS={ts.get('subject')!r} CLI={py.get('subject')!r}")

    ts_res, py_res = norm_resolved(ts["parsed"]["resolved"]), norm_resolved(py["parsed"]["resolved"])
    if ts_res != py_res:
        for i in sorted(set(ts_res) | set(py_res)):
            if ts_res.get(i) != py_res.get(i):
                blocking.append(f"parsed resolved[{i}] differs")
    if sorted(ts["parsed"]["drop"]) != sorted(py["parsed"]["drop"]):
        blocking.append(f"parsed drop differs: TS={ts['parsed']['drop']} CLI={py['parsed']['drop']}")

    # Guardrail verdict per edit. TS keeps blocked edits as suggestions; the CLI records the
    # gate verdict separately, so compare verdicts rather than surviving edits.
    ts_gate = {
        s["nodePath"][-1] if s.get("nodePath") else -1: s["guardrail"] == "ok"
        for s in ts.get("suggestions", []) if s.get("type") == "ref"
    }
    py_gate = {r["i"]: r["gate_ok"] for r in py.get("resolved", [])}
    ts_by_index = {}
    ts_path_by_index = {}
    for s in ts.get("suggestions", []):
        if s.get("type") != "ref":
            continue
        # match on original text — nodePath is an ADF path, not a block index
        ts_by_index[s["original"]] = s["guardrail"] == "ok"
        ts_path_by_index[s["original"]] = s.get("nodePath") or []

    # Per-edit verdict table. Both-blocked agreement was previously invisible: the old code
    # only flagged DISAGREEMENT, so a matching pair of blocks passed silently and could not be
    # counted. The whole point of the fixtures is to make that case observable.
    verdicts = []
    for r in py.get("resolved", []):
        ts_ok = ts_by_index.get(r["original"])
        if ts_ok is None:
            if r["original"] == r["proposed"]:
                continue  # TS drops no-op edits before emitting a suggestion
            blocking.append(f"edit at [{r['i']}] present in CLI, absent in TS")
            verdicts.append({"i": r["i"], "ts": "absent",
                             "cli": "ok" if r["gate_ok"] else "blocked", "agree": False})
            continue
        agree = ts_ok == r["gate_ok"]
        if not agree:
            blocking.append(
                f"guardrail verdict differs at [{r['i']}]: "
                f"TS={'ok' if ts_ok else 'blocked'} CLI={'ok' if r['gate_ok'] else 'blocked'}")
        verdicts.append({
            "i": r["i"],
            "ts": "ok" if ts_ok else "blocked",
            "cli": "ok" if r["gate_ok"] else "blocked",
            "agree": agree,
        })
        # Same-span check: fixtures set nodePath = [blockIndex], so the two sides must agree on
        # WHICH span was blocked, not merely that something was.
        if ts.get("fixture"):
            path = ts_path_by_index.get(r["original"]) or []
            if path and path[-1] != r["i"]:
                blocking.append(
                    f"span mismatch at CLI index [{r['i']}]: TS anchored at {path}")
        if r["heading_skip"]:
            expected.append(
                f"[{r['i']}] heading block — CLI skips it for reference resolution, app does not")

    blocked_shown = [s for s in ts.get("suggestions", []) if s.get("guardrail") == "blocked"]
    if blocked_shown:
        expected.append(
            f"{len(blocked_shown)} edit(s) blocked by the guardrail — displayed as `blocked` by the "
            "app, discarded silently by the CLI")

    model_agreement = None
    if py.get("mode") == "live" and "own_parsed" in py:
        own = norm_resolved(py["own_parsed"].get("resolved", []))
        model_agreement = {
            "same_resolved": own == ts_res,
            "same_drop": sorted(py["own_parsed"].get("drop", [])) == sorted(ts["parsed"]["drop"]),
        }

    # A fixture declares which block indices MUST be blocked. Without this a fixture that
    # failed to violate anything would report "both ok" and pass as agreement — proving
    # nothing while looking green.
    both_blocked = sorted(v["i"] for v in verdicts if v["ts"] == "blocked" and v["cli"] == "blocked")
    if ts.get("fixture"):
        for i in ts.get("expectBlocked", []):
            if i not in both_blocked:
                got = next((v for v in verdicts if v["i"] == i), None)
                blocking.append(
                    f"fixture expected block [{i}] to be BLOCKED by both; got "
                    + (f"TS={got['ts']} CLI={got['cli']}" if got else "no edit emitted at all"))
        for i in ts.get("expectOk", []):
            got = next((v for v in verdicts if v["i"] == i), None)
            if got and not (got["ts"] == "ok" and got["cli"] == "ok"):
                blocking.append(
                    f"fixture expected block [{i}] to stay OK in both; got "
                    f"TS={got['ts']} CLI={got['cli']}")

    return {
        "pageId": ts["pageId"],
        "title": ts.get("title", ts["pageId"]),
        "fixture": bool(ts.get("fixture")),
        "violationClass": ts.get("violationClass"),
        "blocking": blocking,
        "expected": expected,
        "verdicts": verdicts,
        "both_blocked": both_blocked,
        "model_agreement": model_agreement,
        "counts": {
            "blocks": len(ts["parsed"]["resolved"]) + len(ts["parsed"]["drop"]),
            "ts_suggestions": len(ts.get("suggestions", [])),
            "cli_resolved": len(py.get("resolved", [])),
            "cli_drop": len(py.get("drop", [])),
            "both_ok": sum(1 for v in verdicts if v["ts"] == "ok" and v["cli"] == "ok"),
            "both_blocked": len(both_blocked),
            "disagree": sum(1 for v in verdicts if not v["agree"]),
        },
    }


def main() -> int:
    ts_dir, py_dir = CROSSCHECK / "ts", CROSSCHECK / "py"
    if not ts_dir.is_dir() or not py_dir.is_dir():
        print("Missing crosscheck/ts or crosscheck/py — run both sides first.", file=sys.stderr)
        return 2

    results = []
    for ts_file in sorted(ts_dir.glob("*.json")):
        ts = json.loads(ts_file.read_text(encoding="utf-8"))
        if ts.get("empty"):
            continue
        py_file = py_dir / ts_file.name
        if not py_file.is_file():
            print(f"  {ts['pageId']} — no Python artifact, skipped", file=sys.stderr)
            continue
        results.append(compare_page(ts, json.loads(py_file.read_text(encoding="utf-8"))))

    if not results:
        print("Nothing to compare.", file=sys.stderr)
        return 2

    total_blocking = sum(len(r["blocking"]) for r in results)
    lines = [
        "# Forge app ↔ CLI cross-check (§7.5)",
        "",
        f"Pages compared: **{len(results)}** · blocking divergences: **{total_blocking}**",
        "",
        "Both implementations were given the *same extracted ADF blocks* and the *same raw model "
        "response*, so any difference below is implementation drift, not model nondeterminism.",
        "",
        "| Page | TS suggestions | CLI resolved | CLI drop | Blocking | Expected |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        c = r["counts"]
        lines.append(
            f"| {r['title']} | {c['ts_suggestions']} | {c['cli_resolved']} | {c['cli_drop']} "
            f"| {len(r['blocking'])} | {len(r['expected'])} |")

    # ---- guardrail verdict evidence (the M5 gap this closes) --------------------------
    total_both_ok = sum(r["counts"]["both_ok"] for r in results)
    total_both_blocked = sum(r["counts"]["both_blocked"] for r in results)
    total_disagree = sum(r["counts"]["disagree"] for r in results)
    fixtures = [r for r in results if r["fixture"]]
    fixtures_with_agreed_block = [r for r in fixtures if r["both_blocked"]]

    lines += [
        "",
        "## Guardrail verdict agreement",
        "",
        f"Edits compared: **{total_both_ok + total_both_blocked + total_disagree}** · "
        f"both ok: **{total_both_ok}** · both blocked: **{total_both_blocked}** · "
        f"disagreements: **{total_disagree}**",
        "",
        "`ok`/`ok` agreement only shows the two implementations agree when there is nothing to "
        "block. A `blocked`/`blocked` pair is the property the harness exists to verify: that "
        "both sides independently refuse the *same* edit at the *same* span.",
        "",
    ]
    if any(r["verdicts"] for r in results):
        lines += ["| Page | Block | TS | CLI | Agree |", "|---|---|---|---|---|"]
        for r in results:
            for v in r["verdicts"]:
                mark = "yes" if v["agree"] else "**NO**"
                lines.append(f"| {r['title']} | {v['i']} | {v['ts']} | {v['cli']} | {mark} |")
        lines.append("")

    if fixtures:
        ok_count = len(fixtures_with_agreed_block)
        verdict = "PASS" if ok_count >= 3 else "FAIL"
        lines += [
            f"**Fixture acceptance ({verdict}):** {ok_count} of {len(fixtures)} fixtures produced "
            f"a same-span `blocked` result in *both* implementations (threshold: 3).",
            "",
        ]
        for r in fixtures:
            state = f"blocked at {r['both_blocked']}" if r["both_blocked"] else "no agreed block"
            lines.append(f"- `{r['pageId']}` — {r['violationClass']} → {state}")
        lines.append("")

    lines += ["", "## Blocking divergences", ""]
    if total_blocking == 0:
        lines.append("None. Prompts, parsing and guardrail verdicts are identical on every page.")
    else:
        for r in results:
            for b in r["blocking"]:
                lines.append(f"- **{r['title']}** — {b}")

    lines += ["", "## Expected divergences (by design)", ""]
    any_expected = False
    for r in results:
        for e in r["expected"]:
            lines.append(f"- **{r['title']}** — {e}")
            any_expected = True
    if not any_expected:
        lines.append("None encountered on these pages.")
    lines += [
        "",
        "Segmentation (CLI sentences vs ADF blocks) is the third by-design difference. This "
        "harness neutralises it by feeding both sides the same blocks, so it is not measured "
        "here — it is a property of the input, not of the formatter.",
        "",
    ]

    agreements = [r for r in results if r["model_agreement"]]
    if agreements:
        lines += ["## Model agreement (informational)", ""]
        for r in agreements:
            m = r["model_agreement"]
            lines.append(
                f"- **{r['title']}** — same resolved: {m['same_resolved']}, same drop: {m['same_drop']}")
        lines += ["", "Disagreement here is model nondeterminism at temperature 0, not drift.", ""]

    report = CROSSCHECK / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    # Echo the whole report: a head-truncated preview cut the page table mid-way and made a
    # complete run look like it had dropped a page.
    print("\n".join(lines))
    print(f"wrote {report}")
    return 1 if total_blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
