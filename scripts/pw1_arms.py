"""B5 — the PW-1 arms: score every cell under S0/S1/S2/S3 and classify.

Runs entirely off persisted retrieval. No embedding, no retrieval, no model is loaded: the ranked
lists come from `_arm_inputs` (family 1, written by `common_size_ci.py`) and from the published
`per_query.jsonl` (family 2 and the secondary family). Only the provenance attribution changes
between rungs.

Everything decision-bearing was declared before this ran, in
`posthoc_PW1_ARM_DECLARATIONS.md` (D-1..D-7) and `posthoc_PW1_provenance_width.json`:

  D-1  `full_significant` and `delta_full` are READ from the stamped freeze, never recomputed.
       The frozen applicable-cell counts (3/1/0) are asserted before anything is computed.
  D-2  p-values by `exact_signflip_p` (already the closed form; see the declarations).
  D-3  Holm's family is the CELLS AT S2. S1 and S3 are descriptive.
  D-4  CI = paired_bootstrap_diff, percentile, iters 10000, seed 1337, ci 0.95.
  D-6  `r > 1.0` is an ASSERTION, not a diagnostic. `r < 0` is legitimate and must not halt.
  D-7  S0 is arm zero: it must reproduce the stamped levels and delta exactly, and the
       unformatted arm's hit vector must be IDENTICAL across all four rungs.

The run reads its output ONCE.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src import config as C  # noqa: E402
from src.chunkers.base import ChunkContext, Unit  # noqa: E402
from src.datasets import load_track_dataset  # noqa: E402
from src.datasets.base import GoldSpan, Query  # noqa: E402
from src.index.embed import Embedder  # noqa: E402
from src.llm.client import LLMClient, build_llm  # noqa: E402
from src.pw1.interpret import (aggregate, classify_cell,  # noqa: E402
                               holm_within_family, retention_ratio)
from src.pw1.tight_provenance import build_tight_units  # noqa: E402
from src.score.provenance import ANY, is_hit  # noqa: E402
from src.stats.tests import (exact_signflip_p, paired_bootstrap_diff,  # noqa: E402
                             paired_permutation_p)

SCORINGS = ("S0", "S1", "S2", "S3")
K = 5
ITERS, SEED, CI = 10000, 1337, 0.95          # D-4
FREEZE = ROOT / "posthoc_PW1_provenance_width.json"

MINILM, BGE = "all-MiniLM-L6-v2", "BAAI/bge-base-en-v1.5"
FMT256 = {"chunk_tokens": 256, "overlap_frac": 0.0, "reference_resolution": True,
          "dedup": True, "right_size": True, "soft_target_tokens": 384,
          "verbatim_guardrail": True, "diff_gate": True}
C4_PARAMS = {**FMT256, "chunk_tokens": 768}

F1_ARTIFACT = {(MINILM, "A"): "guard1_family1_minilm_A.json",
               (MINILM, "B"): "guard1_family1_minilm_B.json",
               (BGE, "A"): "guard1_family1_bge_A.json",
               (BGE, "B"): "guard1_family1_bge_B.json"}
COMPOSITION_SRC = {MINILM: "rag-formatter-results.zip", BGE: "results_v13"}


def _no_network(self, prompt, system):  # noqa: ANN001, ARG001
    raise RuntimeError("cache miss — the arms are cache-only and must not call the API")


# ---------------------------------------------------------------- scoring

def _hits(rows: list, ranges_by_id: dict) -> list[int]:
    out = []
    for r in rows:
        q = Query(query_id=r["query_id"], text="",
                  gold_spans=[GoldSpan(doc_id=g["doc_id"], start_char=g["start_char"],
                                       end_char=g["end_char"]) for g in r["gold_spans"]])
        hit = 0
        for uid in r["retrieved_unit_ids"][:K]:
            rng = ranges_by_id.get(uid)
            if rng is None:
                raise RuntimeError(f"retrieved unit {uid} absent from the inventory")
            u = Unit(unit_id=uid, text="", doc_id=uid.split(":")[1] if ":" in uid else "",
                     source_ranges=rng)
            u.doc_id = _doc_of(uid, ranges_by_id)
            if is_hit(u, q, variant=ANY, min_overlap=1):
                hit = 1
                break
        out.append(hit)
    return out


_DOC: dict = {}


def _doc_of(uid: str, _r) -> str:
    return _DOC.get(uid, "")


def _ladder_ranges(tight_units) -> dict[str, dict]:
    """unit_id -> {S0..S3: ranges}, from the four-component decomposition."""
    out = {}
    for t in tight_units:
        _DOC[t.unit_id] = t.doc_id
        out[t.unit_id] = {s: [tuple(x) for x in getattr(t, s)] for s in SCORINGS}
    return out


def _flat_ranges(units) -> dict[str, dict]:
    """The unformatted arm: identical at every rung — it has no width to strip (D-7)."""
    out = {}
    for u in units:
        uid = u["unit_id"] if isinstance(u, dict) else u.unit_id
        rng = [tuple(x) for x in (u["source_ranges"] if isinstance(u, dict) else u.source_ranges)]
        _DOC[uid] = u["doc_id"] if isinstance(u, dict) else u.doc_id
        out[uid] = {s: rng for s in SCORINGS}
    return out


# ---------------------------------------------------------------- cells

def family1_cell(emb: str, track: str, ctx, dataset):
    art = json.loads((ROOT / "results_pw1" / F1_ARTIFACT[(emb, track)])
                     .read_text(encoding="utf-8"))
    art = art[0] if isinstance(art, list) else art
    ai = art["_arm_inputs"]
    orig = _flat_ranges(ai["original_256"]["units"])
    tights = [t for d in dataset.documents
              for t in build_tight_units(d, FMT256, ctx, condition_id="fmt256")]
    fmt = _ladder_ranges(tights)
    return ai["original_256"]["per_query"], orig, ai["formatted_256"]["per_query"], fmt


def composition_cell(emb: str, track: str, ctx, dataset, params):
    src = COMPOSITION_SRC[emb]
    if src.endswith(".zip"):
        with zipfile.ZipFile(ROOT / src) as z:
            lines = z.read("per_query.jsonl").decode("utf-8").splitlines()
    else:
        lines = (ROOT / src / "per_query.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [r for r in (json.loads(x) for x in lines) if r.get("track") == track]
    c0 = [r for r in rows if r["condition"] == "C0"]
    c4 = [r for r in rows if r["condition"] == "C4"]

    from src.chunkers import build_chunker
    from src.pipeline import build_units
    from src.run import NO_SWEEP_PARAMS
    cc = C.load_condition("C0")
    cc["params"] = {**cc.get("params", {}), **NO_SWEEP_PARAMS.get("C0", {})}
    orig = _flat_ranges(build_units(build_chunker(cc, ctx), dataset))
    tights = [t for d in dataset.documents
              for t in build_tight_units(d, params, ctx, condition_id="C4")]
    return c0, orig, c4, _ladder_ranges(tights)


# ---------------------------------------------------------------- main

def main() -> int:
    LLMClient._call_provider = _no_network
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    fam = freeze["families"]
    print(f"PW-1 ARMS  ·  freeze {freeze['frozen_utc']}  ·  D-1..D-7 declared beforehand\n")

    base = C.load_default()
    base.setdefault("_cache_root", str(ROOT / "cache"))
    base["llm"]["provider"] = "anthropic"

    plan = [("family_1_primary", e, t) for e in (MINILM, BGE) for t in ("A", "B")] + \
           [("family_2_primary", e, "A") for e in (MINILM, BGE)] + \
           [("family_secondary", e, "B") for e in (MINILM, BGE)]

    ctxs, results, halts = {}, [], []
    for fname, emb, track in plan:
        cell = next(c for c in fam[fname]["cells"]
                    if c["embedder"] == emb and c["track"] == track)
        if track not in ctxs:
            traw = C.load_track(track)
            tm = traw.get("params", {}).get("llm_model")
            tcfg = C.deep_merge(base, {"llm": {"model": tm}}) if tm else base
            ds = load_track_dataset(traw, tcfg["seed"])
            ctxs[track] = (ds, ChunkContext(embedder=Embedder(tcfg, cache_root=tcfg["_cache_root"]),
                                            llm=build_llm(tcfg), config=tcfg))
        ds, ctx = ctxs[track]

        if fname == "family_1_primary":
            orows, orng, frows, frng = family1_cell(emb, track, ctx, ds)
        else:
            params = C4_PARAMS
            orows, orng, frows, frng = composition_cell(emb, track, ctx, ds, params)

        levels, deltas, ovecs = {}, {}, {}
        for s in SCORINGS:
            ov = _hits(orows, {k: v[s] for k, v in orng.items()})
            fv = _hits(frows, {k: v[s] for k, v in frng.items()})
            ovecs[s] = ov
            levels[s] = (sum(ov) / len(ov), sum(fv) / len(fv))
            deltas[s] = (sum(fv) / len(fv)) - (sum(ov) / len(ov))
            if s == "S0":
                s0_vecs = (ov, fv)
            else:
                globals().setdefault("_v", {})[s] = (ov, fv)

        # ---- D-7: S0 must reproduce the stamped values ----
        pl = cell["published_levels"]
        want_o, want_f = (pl.get("orig256", pl.get("C0")), pl.get("fmt256", pl.get("C4")))
        got_o, got_f = levels["S0"]
        if round(got_o, 4) != want_o or round(got_f, 4) != want_f or \
           round(deltas["S0"], 4) != cell["delta_full"]:
            halts.append(f"D-7 S0 MISMATCH {fname} {emb}/{track}: "
                         f"levels {got_o:.4f}/{got_f:.4f} vs {want_o}/{want_f}, "
                         f"delta {deltas['S0']:+.4f} vs {cell['delta_full']:+.4f}")
            print(f"  *** {halts[-1]}")
            continue
        # ---- D-7 companion: orig invariant across the ladder ----
        if any(ovecs[s] != ovecs["S0"] for s in SCORINGS):
            halts.append(f"D-7 ORIG NOT INVARIANT {fname} {emb}/{track}")
            print(f"  *** {halts[-1]}")
            continue

        results.append({"family": fname, "embedder": emb, "track": track,
                        "delta_full": cell["delta_full"],
                        "full_significant": cell["branch_1"] == "APPLICABLE",
                        "levels": {s: [round(a, 4), round(b, 4)] for s, (a, b) in levels.items()},
                        "delta": {s: round(d, 4) for s, d in deltas.items()},
                        "_vec": {s: (ovecs[s], None) for s in SCORINGS},
                        "_fmt": frows, "_frng": frng, "_orows": orows, "_orng": orng})
        print(f"  {fname:18}{emb[:22]:24}{track}  S0 reproduces "
              f"({got_o:.4f}/{got_f:.4f}, {deltas['S0']:+.4f})  orig invariant  OK")

    if halts:
        print("\nHALT — D-7 failed. No corrected value is read.")
        for h in halts:
            print(f"  {h}")
        return 1

    print(f"\nD-7 PASSED on all {len(results)} cells. Proceeding to the corrected rungs.\n")

    # ---- statistics per cell per rung: D-2 exact p, D-4 CI ----
    for res in results:
        orows = res.pop("_orows"); orng = res.pop("_orng")
        frows = res.pop("_fmt"); frng = res.pop("_frng")
        res.pop("_vec", None)
        stats, exact_delta = {}, {}
        for s in SCORINGS:
            ov = _hits(orows, {k: v[s] for k, v in orng.items()})
            fv = _hits(frows, {k: v[s] for k, v in frng.items()})
            d = paired_bootstrap_diff(fv, ov, ITERS, SEED, CI)
            ex = exact_signflip_p(fv, ov)
            exact_delta[s] = sum(fv) / len(fv) - sum(ov) / len(ov)   # FULL precision
            stats[s] = {"orig": round(sum(ov) / len(ov), 4),
                        "fmt": round(sum(fv) / len(fv), 4),
                        "delta": round(exact_delta[s], 4),
                        "delta_full_precision": exact_delta[s],
                        "ci95": [round(x, 4) for x in d["ci95"]],
                        "p_exact": float(format(ex["p_exact"], ".6g")),
                        "p_mc_10k": round(paired_permutation_p(fv, ov, ITERS, SEED), 5),
                        "k_discordant": ex["k_discordant"],
                        "n_gains": ex["n_gains"], "n_losses": ex["n_losses"]}

        # `r`'s DENOMINATOR is the D-7-verified full-precision S0 delta, not the stamped 4-dp
        # value. D-7 already asserted that this recomputation reproduces the stamped figure, so
        # it is the same quantity at more digits -- which is what licenses using it. Both sides
        # full precision, rounded once for display (A1f).
        den = exact_delta["S0"]
        if round(den, 4) != res["delta_full"]:
            raise RuntimeError(f"S0 denominator {den} does not round to the stamped "
                               f"{res['delta_full']}")
        # A7 RUNS ON EVERY RUNG THAT COMPUTES r, not only the one that is consumed. C-1 closed
        # this for branches; this is the same defect one level up, for rungs. Frozen
        # halt_conditions says "any cell", and the surface is four rungs x eight cells.
        for s in SCORINGS:
            stats[s]["r"] = retention_ratio(exact_delta[s], den)
        res["stats"] = stats
        res["_den"] = den
        res["_num_S2"] = exact_delta["S2"]

    # ---- D-3: Holm across the CELLS AT S2, per family ----
    for fname in ("family_1_primary", "family_2_primary", "family_secondary"):
        cells = [r for r in results if r["family"] == fname]
        for c, a in zip(cells, holm_within_family([c["stats"]["S2"]["p_exact"]
                                                   for c in cells])):
            c["p_holm_S2"] = float(format(a, ".6g"))

    # ---- classify with the frozen rule; D-1 keeps full_significant from the freeze ----
    for r in results:
        s2 = r["stats"]["S2"]
        # FULL PRECISION on both sides. Passing the rounded s2["delta"] and the stamped
        # delta_full produced a classification r that DISAGREED with the stats r on all eight
        # cells -- two values for one quantity. The exact ratios are small-integer fractions
        # (15/27, 16/26, -2/10); rounding either side destroys that.
        r["classification"] = classify_cell(
            delta_full=r["_den"], full_significant=r["full_significant"],
            delta_corrected=r["_num_S2"], ci_corrected=tuple(s2["ci95"]),
            p_holm_corrected=r["p_holm_S2"])
        if r["classification"]["r"] is not None:
            assert abs(r["classification"]["r"] - s2["r"]) < 1e-12,                 "classification r must equal the reported stats r -- one quantity, one value"
        r.pop("_den"); r.pop("_num_S2")

    print(f"{'family':17}{'embedder':15}{'t':2}{'rung':5}{'orig':>8}{'fmt':>8}{'delta':>9}"
          f"{'95% CI':>19}{'K':>4}{'p_exact':>10}{'r':>9}")
    for r in results:
        for s in SCORINGS:
            v = r["stats"][s]
            ci = f"[{v['ci95'][0]:+.4f},{v['ci95'][1]:+.4f}]"
            rv = "n/a" if v["r"] is None else format(v["r"], "+.4f")
            print(f"{r['family'][:16]:17}{r['embedder'][:13]:15}{r['track']:2}{s:5}"
                  f"{v['orig']:8.4f}{v['fmt']:8.4f}{v['delta']:+9.4f}{ci:>19}"
                  f"{v['k_discordant']:4}{v['p_exact']:10.5f}{rv:>9}")
        c = r["classification"]
        rr = "n/a" if c["r"] is None else round(c["r"], 4)
        print(f"{'':17}{'':15}{'':2}--> {c['branch']}   r={rr}   "
              f"p_holm_S2={r['p_holm_S2']:.6g}\n")

    headline = {}
    for fname in ("family_1_primary", "family_2_primary", "family_secondary"):
        labels = [r["classification"]["branch"] for r in results if r["family"] == fname]
        agg = aggregate(labels)
        # An EMPTY family and an UNDERPOWERED one are different states and must not render
        # identically -- the BLOCKED/ENVIRONMENT principle: attempted-and-blocked must never
        # look like never-attempted. `aggregate()` returns UNDERPOWERED for both, so the
        # distinction is drawn here, in the reporting layer, and named.
        n_applicable = sum(1 for l in labels if l != "NOT APPLICABLE")
        if agg == "UNDERPOWERED" and n_applicable == 0:
            agg = "NO APPLICABLE CELLS"
        headline[fname] = {"label": agg, "n_cells": len(labels),
                           "n_applicable": n_applicable,
                           "n_powered": sum(1 for l in labels
                                            if l not in ("NOT APPLICABLE", "UNDERPOWERED"))}
    print("HEADLINE per family — least favourable among applicable AND powered; never merged.")
    print("  applicable = branch 1 did not fire (delta_full significant per the FROZEN input)")
    print("  powered    = branch 2 did not fire (the S2 CI does not contain BOTH 0 and delta_full)")
    for k, v in headline.items():
        print(f"  {k:20} {v['label']:22} cells={v['n_cells']} applicable={v['n_applicable']} "
              f"powered={v['n_powered']}")

    out = {"freeze": freeze["frozen_utc"],
           "declarations": "posthoc_PW1_ARM_DECLARATIONS.md",
           "d7": "passed on all 8 cells",
           "holm_scope": "D-3: the cells at S2; S1 and S3 descriptive",
           "cells": results, "headline_per_family": headline}
    (ROOT / "results_pw1" / "arms.json").write_text(json.dumps(out, indent=2),
                                                    encoding="utf-8")
    print(f"\nwrote {ROOT / 'results_pw1' / 'arms.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
