"""v1.2 decision bundle writer (§6). The §5 decision must be computable from results.json."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.stats.tests import bootstrap_ci_mean

PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9"]
CONDS = ["C0", "C2", "C4", "C4i"]
K = [1, 3, 5, 10]


def _cond_block(bundle, cid, track, prompts_ver):
    res = bundle["results"][cid]
    m = res.metrics["hybrid"]["any"]
    pq = m["_per_query"]["recall_at_k"]
    ci = {}
    for k in K:
        _, lo, hi = bootstrap_ci_mean(pq.get(k, []), iters=10000, seed=1337)
        ci[str(k)] = [round(lo, 4), round(hi, 4)]
    return {
        "track": track, "condition": cid, "prompts_version": prompts_ver,
        "n_queries": res.n_queries,
        "recall_at_k": {str(k): round(m["recall_at_k"].get(k, 0.0), 4) for k in K},
        "recall_at_k_ci95": ci,
        "dense": {"recall_at_k": {"5": round(res.metrics["dense"]["any"]["recall_at_k"].get(5, 0.0), 4)}},
        "hybrid": {"recall_at_k": {"5": round(m["recall_at_k"].get(5, 0.0), 4)}},
        "chunk_stats": res.chunk_stats,
        "cost": bundle["cost"].get(cid, {}),
    }


def write_all(out: Path, p: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig = out / "figures"
    fig.mkdir(exist_ok=True)

    rj = {
        "experiment": p["experiment"], "created_utc": p["created_utc"],
        "preregistration_hash": p["preregistration_hash"],
        "exclusion_list_hash": p["exclusion_list_hash"], "doc_list_hash": p["doc_list_hash"],
        "prompts_version_by_condition": p["prompts_version_by_condition"],
        "b2_meta": p["b2_meta"],
        "results": ([_cond_block(p["b2"], c, "B2", p["prompts_version_by_condition"][c]) for c in CONDS]
                    + [_cond_block(p["a"], c, "A", p["prompts_version_by_condition"][c]) for c in CONDS]),
        "pairwise": p["pairwise"],
        "subgroup": p["subgroup"],
        "identity_checks": p["identity_checks"],
        "readability3way": p["readability3way"],
        "a_regression": p["a_regression"],
        "guardrail": p["guardrail"],
        "cost": p["b2_cost"],
        "verdict": p["verdict"],
    }
    (out / "results.json").write_text(json.dumps(rj, indent=2), encoding="utf-8")

    # per_query.jsonl for B2 (with identity tag)
    with open(out / "per_query.jsonl", "w", encoding="utf-8") as f:
        for cid in CONDS:
            for rec in p["b2"]["results"][cid].per_query:
                tag = p["tags"].get(rec["query_id"])
                f.write(json.dumps({"track": "B2", "condition": cid, "identity_tag": tag, **rec},
                                   ensure_ascii=False) + "\n")

    _figures(fig, rj, p)
    _markdown(out, rj, p)


def _figures(fig: Path, rj: dict, p: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows = {r["condition"]: r for r in rj["results"] if r["track"] == "B2"}

    # 1) b2_recall_by_condition (recall@5 with CI)
    fig1, ax = plt.subplots(figsize=(7, 4.5))
    conds = [c for c in CONDS if c in rows]
    vals = [rows[c]["recall_at_k"]["5"] for c in conds]
    cis = [rows[c]["recall_at_k_ci95"]["5"] for c in conds]
    err = [[v - lo for v, (lo, hi) in zip(vals, cis)], [hi - v for v, (lo, hi) in zip(vals, cis)]]
    ax.bar(conds, vals, yerr=err, capsize=4, color=[PALETTE[i] for i in range(len(conds))])
    ax.set_ylabel("Recall@5 (B2, hybrid)"); ax.set_ylim(0, max(vals) * 1.3 + 0.05)
    ax.set_title("B2 recall@5 by condition (95% CI)")
    fig1.savefig(fig / "b2_recall_by_condition.svg", bbox_inches="tight")
    fig1.savefig(fig / "b2_recall_by_condition.png", dpi=300, bbox_inches="tight")
    plt.close(fig1)
    _csv(fig / "b2_recall_by_condition.csv", ["condition", "recall5", "ci_lo", "ci_hi"],
         [[c, v, lo, hi] for c, v, (lo, hi) in zip(conds, vals, cis)])

    # 2) subgroup_effect (headline): C4i-C4 delta in poor vs rich
    sg = p["subgroup"]
    fig2, ax = plt.subplots(figsize=(6, 4.5))
    grps = [g for g in ("identity_poor", "identity_rich") if sg.get(g, {}).get("n")]
    deltas = [sg[g]["delta"] for g in grps]
    errs = [[sg[g]["delta"] - sg[g]["ci95"][0] for g in grps], [sg[g]["ci95"][1] - sg[g]["delta"] for g in grps]]
    ax.bar([f"{g}\n(n={sg[g]['n']})" for g in grps], deltas, yerr=errs, capsize=5,
           color=[PALETTE[2], PALETTE[1]][: len(grps)])
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_ylabel("Δ recall@5 (C4i − C4)")
    ax.set_title("Subgroup effect (H5a) — the headline")
    fig2.savefig(fig / "subgroup_effect.svg", bbox_inches="tight")
    fig2.savefig(fig / "subgroup_effect.png", dpi=300, bbox_inches="tight")
    plt.close(fig2)
    _csv(fig / "subgroup_effect.csv", ["subgroup", "n", "c4", "c4i", "delta", "ci_lo", "ci_hi"],
         [[g, sg[g]["n"], sg[g]["c4_recall5"], sg[g]["c4i_recall5"], sg[g]["delta"],
           sg[g]["ci95"][0], sg[g]["ci95"][1]] for g in grps])

    # 3) stamps_distribution
    stamps = p["identity_checks"].get("stamps_per_doc", [])
    fig3, ax = plt.subplots(figsize=(6, 4))
    if stamps:
        ax.hist(stamps, bins=range(0, max(stamps) + 2), color=PALETTE[0], align="left", rwidth=0.85)
    ax.set_xlabel("identity stamps per document"); ax.set_ylabel("docs")
    ax.set_title("Stamps-per-document (over-stamping guard, H5c)")
    fig3.savefig(fig / "stamps_distribution.svg", bbox_inches="tight")
    fig3.savefig(fig / "stamps_distribution.png", dpi=300, bbox_inches="tight")
    plt.close(fig3)
    _csv(fig / "stamps_distribution.csv", ["stamps_per_doc"], [[s] for s in stamps])


def _csv(path: Path, header, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def _markdown(out: Path, rj: dict, p: dict) -> None:
    v = rj["verdict"]; sg = rj["subgroup"]; g = rj["guardrail"]; r3 = rj["readability3way"]
    rows = {r["condition"]: r for r in rj["results"] if r["track"] == "B2"}
    L = ["# v1.2 — Document-Identity Injection — Results\n"]
    L.append(f"**UTC:** {rj['created_utc']} · **prereg:** `{rj['preregistration_hash'][:12]}…` · "
             f"**doc-list:** `{rj['doc_list_hash'][:12]}…` · **exclusion:** `{rj['exclusion_list_hash'][:12]}…`\n")
    L.append("## TL;DR verdict\n")
    L.append(f"**Decision: {v['decision']}** — H5 {v['H5']}, H5a {v['H5a']}, H5b {v['H5b']}, H5c {v['H5c']}.\n")
    L.append(f"> {v['notes']}\n")
    L.append(f"\n> Decided on **Track B2** ({rj['b2_meta']['n_queries']} fresh held-out queries, "
             f"{rj['b2_meta']['n_identity_poor']} identity_poor / {rj['b2_meta']['n_identity_rich']} rich, "
             f"{rj['b2_meta']['n_docs']} docs). The old B-150 is **development data (contaminated — the "
             f"idea was derived from its failures)** and plays no part in this decision.\n")

    L.append("\n## B2 headline (recall@5, hybrid; 95% CI)\n")
    L.append("| Condition | prompts | recall@5 [CI] | dense@5 | units | fresh/cached |")
    L.append("|---|---|---|---|---|---|")
    for c in CONDS:
        r = rows[c]; ci = r["recall_at_k_ci95"]["5"]; cost = r["cost"]
        L.append(f"| {c} | {r['prompts_version']} | {r['recall_at_k']['5']:.3f} "
                 f"[{ci[0]:.3f},{ci[1]:.3f}] | {r['dense']['recall_at_k']['5']:.3f} | "
                 f"{r['chunk_stats']['index_units']} | "
                 f"{cost.get('fresh_calls', 0)}/{cost.get('cached_calls', 0)} |")

    L.append("\n### Significance (paired bootstrap + Holm) — the H5 family\n")
    L.append("| Pair | Δrecall@5 | 95% CI | p | p(Holm) | CI excludes 0 |")
    L.append("|---|---|---|---|---|---|")
    for pw in rj["pairwise"]:
        L.append(f"| {pw['pair']} | {pw['mean_diff']:+.3f} | [{pw['ci95'][0]:+.3f},{pw['ci95'][1]:+.3f}] | "
                 f"{pw['p_value']:.4f} | {pw.get('p_holm', float('nan')):.4f} | "
                 f"{'yes' if pw['significant'] else 'no'} |")

    L.append("\n## Subgroup effect (H5a) — the mechanism test\n")
    L.append("![subgroup](figures/subgroup_effect.svg)\n")
    L.append("| Subgroup | n | C4 | C4i | Δ (C4i−C4) | 95% CI | sig |")
    L.append("|---|---|---|---|---|---|---|")
    for grp in ("identity_poor", "identity_rich"):
        s = sg.get(grp, {})
        if s.get("n"):
            L.append(f"| {grp} | {s['n']} | {s['c4_recall5']:.3f} | {s['c4i_recall5']:.3f} | "
                     f"{s['delta']:+.3f} | [{s['ci95'][0]:+.3f},{s['ci95'][1]:+.3f}] | "
                     f"{'yes' if s['significant'] else 'no'} |")

    L.append("\n## Guardrail (H5b)\n")
    L.append(f"- preserved-term failures: **{g['preserved_term_failures']}** (target 0)")
    L.append(f"- identity-source violations: **{g['source_violations']}** (target 0)")
    L.append(f"- hybrid tracks dense: **{g['hybrid_tracks_dense']}** (C4i hybrid {g['c4i_hybrid5']:.3f} "
             f"vs dense {g['c4i_dense5']:.3f})")

    L.append("\n## Readability 3-way (H5c)\n")
    L.append(f"- original {r3['original']:.2f} · C4 {r3['c4']:.2f} · C4i {r3['c4i']:.2f} "
             f"(n={r3['n']}); C4i must be within 0.15 of both.")
    ic = rj["identity_checks"]
    sp = ic.get("stamps_per_doc", [])
    L.append(f"- identity stamps: total {ic['stamps_total']}, per-doc mean "
             f"{(sum(sp) / len(sp)) if sp else 0:.2f} / max {max(sp) if sp else 0}. "
             "![stamps](figures/stamps_distribution.svg)")

    L.append("\n## Track A regression (safety, not a decision input)\n")
    ar = rj["a_regression"]
    L.append(f"C4 {ar['c4']:.3f} vs C4i {ar['c4i']:.3f} (Δ={ar['delta']:+.3f}, "
             f"CI [{ar['ci95'][0]:+.3f},{ar['ci95'][1]:+.3f}]); within CI of C4: **{ar['within_ci_of_c4']}** "
             "(pre-registered expectation: C4i ≈ C4 on identity-rich synthetic data).")

    L.append("\n## Cost\n")
    L.append(f"B2 LLM: {rj['cost']}.\n")

    L.append("\n## Threats to validity\n")
    L.append("- **The old B-150 was development data** — the identity-injection idea was derived from its "
             "failures, so it is contaminated as evidence; this decision uses only the fresh B2 split.")
    L.append("- **v1.2 baselines are NOT numerically comparable to v1.1** (corpus expanded for query supply). "
             "The v1.2 decision is internal to its own corpus (C4i vs C4), which is unaffected.")
    L.append("- **Larger distractor pool** (expanded corpus) increases distractor mass — realistic for real "
             "KBs and favorable to detecting the identity effect; accepted because the corpus was frozen "
             "(doc-list hash) before any treatment metric existed.")
    L.append("- **One-shot rule:** if H5 failed on B2, the feature is not re-tried on B2 — a retry needs a B3 split.")

    L.append("\n## Reproduction\n")
    L.append("```bash\npython -m src.run_v12 --provider anthropic --b2-model claude-sonnet-5 "
             "--a-model claude-opus-4-8\n```\n")
    (out / "results.md").write_text("\n".join(L), encoding="utf-8")
