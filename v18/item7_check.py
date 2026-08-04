"""v1.8 — the item-7 self-check, executed against the FINAL results document.

Item 7, as stated in `Candidates_ScopeOfDirectionTest_2026-07-31.md` §5:

> A claim a document makes about its own contents, where that claim is a count or a universal,
> must name the procedure that produced it — the list counted, the search run — and that
> procedure must be executed against the **final** text rather than the remembered one.

§6 of that document records as open whether item 7 stops at self-descriptions. The results
document asserts counts over the *record* — call totals, discordant counts, row counts — which
sit on the far side of that open question, so the **general form** offered in §6 is adopted as
the standard here: any count or universal asserted over material fixed at writing time.

Each check below (a) re-derives a value from the artifact that defines it, and (b) asserts the
rendered document actually contains that value. Both halves matter: deriving without checking
the text would not catch a transcription slip, and checking the text against a remembered value
would be the failure item 7 exists to prevent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "Results_v18_InstrumentDivergence.md"
RUN = ROOT / "v18" / "results_run"
G0 = ROOT / "v18" / "results_gate0"


def _fmt(x, dp=5, sign=True):
    s = f"{x:+.{dp}f}" if sign else f"{x:.{dp}f}"
    return s


def build() -> dict:
    text = DOC.read_text(encoding="utf-8")
    checks: list[dict] = []

    def check(label, literal, procedure):
        present = str(literal) in text
        checks.append({"claim": label, "value": str(literal), "procedure": procedure,
                       "present_in_final_text": present})

    led = json.loads((G0 / "spend_ledger.json").read_text(encoding="utf-8"))
    det = [e for e in led["entries"] if not e.get("indeterminate")]
    ind = [e for e in led["entries"] if e.get("indeterminate")]

    total = sum(e["calls"] for e in det)
    check("total calls", f"{total:,}", "sum of ledger determinate entries")
    check("frozen projection", f"{led['frozen_projection']:,}", "ledger.frozen_projection")
    check("ceiling", f"{led['ceiling']:,}", "ledger.ceiling")
    check("input tokens", f"{sum(e['input_tokens'] for e in det):,}", "sum of ledger input_tokens")
    check("output tokens", f"{sum(e['output_tokens'] for e in det):,}",
          "sum of ledger output_tokens")
    for e in ind:
        check("probe spend range low", e["calls_low"], "ledger indeterminate entry")
        check("probe spend range high", f"{e['calls_high']:,}", "ledger indeterminate entry")

    for e in det:
        check(f"{e['stage']} calls", f"{e['calls']:,}", "ledger entry")
        check(f"{e['stage']} batch id", e["batch_id"], "ledger entry")

    rows = 0
    for f in ("batch_G", "batch_j1", "batch_j2"):
        m = json.loads((RUN / f"{f}.json").read_text(encoding="utf-8"))
        rows += m["n_answers"]
        assert m["n_answers"] == m["n_requests"], f"{f}: replies != requests"
        assert m["resubmission_rounds_used"] == 0, f"{f}: resubmissions occurred"
        assert m["pin"]["served_model_constant"], f"{f}: served model not constant"
        for b in m["batches"]:
            assert b["n_failed"] == 0, f"{b['stage']}: failed rows"
            check(f"{b['stage']} rows sha256 prefix", b["raw_sha256"][:8],
                  "sha256 of the persisted raw rows file")
    check("total rows across batches", f"{rows:,}", "sum of n_answers over the three batch files")

    sc = json.loads((RUN / "scored.json").read_text(encoding="utf-8"))
    c = sc["contrasts"]
    check("cells scored", sc["n_cells"], "len(per_cell) in score_run")

    for t in ("A", "B"):
        ctx = c[f"context_contrasts_{t}"]
        for key, label in (("total_F768_minus_U256", "total"),
                           ("size_U768_minus_U256", "size"),
                           ("residual_F768_minus_U768", "residual")):
            v = ctx[key]
            check(f"context {label} mean, track {t}", _fmt(v["mean_diff"]),
                  "contrasts.context_contrast_table -> descriptive_contrast.mean_diff")
        check(f"pd2_direction_holds track {t}", ctx["pd2_direction_holds"],
              "context_contrast_table.pd2_direction_holds")

        for group in ("answer_contrasts", "i2_contrasts"):
            for key, v in c[f"{group}_{t}"].items():
                check(f"{group} {key} mean, track {t}", _fmt(v["mean_diff"]),
                      "descriptive_contrast.mean_diff")

        b = c[f"B1_{t}"]
        check(f"B1 mean track {t}", _fmt(b["mean"], 6), "tested_contrast on b1_for_query values")
        check(f"B1 p track {t}", b["p_permutation"], "paired_permutation_p, iters=10000, seed=1337")
        check(f"B1 n track {t}", b["n"], "len of the per-query B1 vector")
        for k in ("favour_positive", "favour_negative", "ties"):
            check(f"B1 {k} track {t}", b["discordant"][k], "tested_contrast.discordant")

    fb = c["F_BIAS"]
    check("F_BIAS p_holm", fb["p_holm"]["B1"], "holm_family over the one declared member")
    assert fb["p_holm"]["B1"] == fb["p_raw"]["B1"], "single-member Holm must be the identity"
    assert list(fb["members"]) == ["B1"], "F_BIAS must have exactly one member"

    h = json.loads((RUN / "hedging_table.json").read_text(encoding="utf-8"))
    check("hedged replies", h["n_hedged"], "hedging.classify over all j1+j2 replies")
    check("total judge replies", f"{h['n_replies']:,}", "len(j1) + len(j2)")
    for k, v in h["by_metric"].items():
        check(f"hedged {k}", v, "hedging.build by_metric")
    for k, v in h["by_track"].items():
        check(f"hedged track {k}", v, "hedging.build by_track")
    for k, v in h["by_track_arm"].items():
        check(f"hedged {k}", v, "hedging.build by_track_arm")

    pd = json.loads((G0 / "probe_disposition.json").read_text(encoding="utf-8"))
    for name, digest in pd["invalid_artifact_sha256"].items():
        check(f"INVALID artifact {name} sha prefix", digest[:8], "sha256 of the retained artifact")

    from v18.codebook import codebook_sha256
    for t in ("A", "B"):
        check(f"codebook {t} sha prefix", codebook_sha256(t)[:8], "sha256 of the frozen codebook")

    # the PF-16 identity claim, re-derived rather than quoted
    import re as _re
    j = {}
    for n in ("replies_j1.json", "replies_j2.json"):
        j.update(json.loads((RUN / n).read_text(encoding="utf-8")))

    def legacy(reply):
        t = reply.strip()
        if t.startswith("```"):
            t = _re.sub(r"^```[a-zA-Z]*\s*", "", t)
            t = _re.sub(r"\s*```$", "", t).strip()
        o = json.loads(t)
        if not isinstance(o, dict):
            raise ValueError
        return o

    from v18.instruments import parse_json_object
    same = diff = only_new = 0
    for r in j.values():
        try:
            old = legacy(r)
        except Exception:
            only_new += 1
            continue
        same += 1 if old == parse_json_object(r) else 0
        diff += 0 if old == parse_json_object(r) else 1
    check("rows identical old vs amended parser", f"{same:,}", "legacy parser vs parse_json_object")
    check("rows differing", diff, "legacy parser vs parse_json_object")
    check("rows only the amendment parses", only_new, "legacy parser raises, amended parses")

    n_missing = [c for c in checks if not c["present_in_final_text"]]
    return {"document": DOC.name, "n_checks": len(checks),
            "n_absent_from_text": len(n_missing),
            "absent": [c["claim"] for c in n_missing], "checks": checks}


def main() -> int:
    rec = build()
    (RUN / "item7_check.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    print(f"item-7 self-check over {rec['document']}")
    print(f"  claims checked against their procedures: {rec['n_checks']}")
    print(f"  claims NOT found verbatim in the final text: {rec['n_absent_from_text']}")
    for a in rec["absent"]:
        print(f"    MISSING: {a}")
    print(f"wrote {RUN / 'item7_check.json'}")
    return 1 if rec["n_absent_from_text"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
