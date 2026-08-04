"""Output artifacts (plan §10): results.json, per_query.jsonl, figures/*, results.md.

Figures use the Okabe-Ito colorblind-safe palette, are labeled, and carry 95% CIs
where applicable. Underlying numbers are also emitted as CSV so charts can be restyled
for the white paper (§10.3, §10.5).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src import config as C
from src.stats.tests import bootstrap_ci_mean

RESULTS = C.ROOT / "results"
FIG = RESULTS / "figures"

# Okabe-Ito colorblind-safe qualitative palette.
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9",
           "#F0E442", "#999999"]
COND_ORDER = ["C0", "C1", "C2", "C3", "C4", "C5",
              "C3-noref", "C3-nosize", "C3-nodedup", "C3-markeronly"]


# --------------------------------------------------------------------------
# results.json
# --------------------------------------------------------------------------
def _ci_all_k(pq_recall: dict, k_values, iters, seed, ci):
    out = {}
    for k in k_values:
        vec = pq_recall.get(k, [])
        _, lo, hi = bootstrap_ci_mean(vec, iters=iters, seed=seed, ci=ci)
        out[str(k)] = [round(lo, 4), round(hi, 4)]
    return out


def assemble_results_json(run_id, created_utc, git_commit, config_digest, cfg, bundles,
                          verdict, prereg_hash) -> dict:
    st = cfg.get("stats", {})
    iters, seed, ci = st.get("bootstrap_iters", 10000), cfg["seed"], st.get("ci", 0.95)
    k_values = cfg.get("retrieval", {}).get("k_values", [1, 3, 5, 10])

    all_conditions = sorted({cid for b in bundles for cid in b["results"]},
                            key=lambda c: COND_ORDER.index(c) if c in COND_ORDER else 99)
    tracks = [b["track"] for b in bundles]
    env = {
        "python": _py_version(), "os": _os_string(),
        "embedding_model": bundles[0]["embedder"].get("model", ""),
        "embedding_revision": bundles[0]["embedder"].get("revision", ""),
        "embedding_backend": bundles[0]["embedder"].get("backend", ""),
        "llm_model": cfg.get("llm", {}).get("model", ""),
        "llm_provider": cfg.get("llm", {}).get("provider", ""),
        "faiss": _pkg_version("faiss"), "seed": seed,
    }

    result_rows = []
    for b in bundles:
        faith_by = b["faithfulness"].get("by_condition", {})
        for cid, res in b["results"].items():
            for variant in ("any", "strict"):
                m = res.metrics["hybrid"][variant]
                dense5 = res.metrics["dense"][variant]["recall_at_k"].get(5, 0.0)
                hyb5 = m["recall_at_k"].get(5, 0.0)
                row = {
                    "track": b["track"], "condition": cid, "n_queries": res.n_queries,
                    "overlap_variant": variant,
                    "recall_at_k": {str(k): round(m["recall_at_k"].get(k, 0.0), 4) for k in k_values},
                    "recall_at_k_ci95": _ci_all_k(m["_per_query"]["recall_at_k"], k_values, iters, seed, ci),
                    "ndcg_at_k": {str(k): round(m["ndcg_at_k"].get(k, 0.0), 4) for k in (5, 10) if k in k_values},
                    "mrr": round(m["mrr"], 4),
                    "dense": {"recall_at_k": {"5": round(dense5, 4)}},
                    "hybrid": {"recall_at_k": {"5": round(hyb5, 4)}},
                    "chunk_stats": res.chunk_stats,
                    # v1.3 reranking axis — present only when the axis was on. Added as an
                    # extra key so every pre-v1.3 field keeps its exact meaning.
                    **({"rerank": {
                        "recall_at_k": {
                            str(k): round(res.metrics["hybrid_rerank"][variant]
                                          ["recall_at_k"].get(k, 0.0), 4) for k in k_values},
                        "mrr": round(res.metrics["hybrid_rerank"][variant]["mrr"], 4),
                        "delta_recall@5": round(
                            res.metrics["hybrid_rerank"][variant]["recall_at_k"].get(5, 0.0)
                            - m["recall_at_k"].get(5, 0.0), 4),
                    }} if "hybrid_rerank" in res.metrics else {}),
                    "faithfulness": {"n": b["faithfulness"].get("n", 0),
                                     "score_mean": faith_by.get(cid, 0.0),
                                     "rubric": b["faithfulness"].get("rubric", "")},
                    "cost": {**{k: res.llm_cost.get(k, 0) for k in
                                ("fresh_calls", "cached_calls", "fresh_tokens", "cached_tokens")},
                             "format_seconds": round(getattr(res, "format_seconds", 0.0), 3),
                             "index_seconds": res.index_seconds},
                }
                result_rows.append(row)

    pairwise = [row for b in bundles for row in b["pairwise"]]
    ablations = [row for b in bundles for row in b["ablations"]]
    readability = bundles[0]["readability"] if bundles else {}
    tracks_meta = [{
        "track": b["track"], "n_test": b["n_test"],
        "faithfulness": {"by_condition": b["faithfulness"].get("by_condition", {}),
                         "n": b["faithfulness"].get("n", 0),
                         "rubric": b["faithfulness"].get("rubric", "")},
        "llm_cost": b["llm_cost"], "readability": b["readability"],
        "common_size": b.get("common_size", {}),
        "llm_model": b.get("llm_model", ""),
    } for b in bundles]

    return {
        "run_id": run_id, "created_utc": created_utc, "git_commit": git_commit,
        "config_digest": config_digest, "environment": env, "tracks": tracks,
        "conditions": all_conditions,
        "chosen_chunk_sizes": bundles[0]["chosen_sizes"] if bundles else {},
        "results": result_rows, "pairwise": pairwise,
        "rerank": {
            "enabled": any(b.get("rerank") for b in bundles),
            "config": next((b["rerank"] for b in bundles if b.get("rerank")), {}),
            "main_effect": [r for b in bundles
                            for r in (b.get("rerank_stats") or {}).get("main_effect", [])],
            "interaction": [(b.get("rerank_stats") or {})["interaction"] for b in bundles
                            if (b.get("rerank_stats") or {}).get("interaction")],
        },
        "ablation_contributions": ablations,
        "readability": {"n_docs": readability.get("n_docs", 0),
                        "c3_mean": round(readability.get("c3_mean", 0.0), 3),
                        "original_mean": round(readability.get("original_mean", 0.0), 3),
                        "preserved_term_failures": readability.get("preserved_term_failures", 0),
                        "rubric": readability.get("rubric", "")},
        "preregistration_hash": prereg_hash,
        "verdict": verdict,
        "tracks_meta": tracks_meta,
    }


def write_all(results_json: dict, bundles, cfg) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(exist_ok=True)
    (RESULTS / "results.json").write_text(json.dumps(results_json, indent=2), encoding="utf-8")
    _write_per_query(bundles)
    _write_figures(results_json, bundles)
    _write_markdown(results_json, bundles, cfg)


def _write_per_query(bundles) -> None:
    path = RESULTS / "per_query.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for b in bundles:
            for cid, res in b["results"].items():
                for rec in res.per_query:
                    out = {"track": b["track"], "condition": cid, **rec}
                    f.write(json.dumps(out, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
def _save(fig, name):
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)


def _csv(name, header, rows):
    with open(FIG / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _rows_for(results_json, track, variant="any"):
    return {r["condition"]: r for r in results_json["results"]
            if r["track"] == track and r["overlap_variant"] == variant}


def _write_figures(results_json, bundles) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    k_values = [1, 3, 5, 10]
    for b in bundles:
        track = b["track"]
        rows = _rows_for(results_json, track)
        conds = [c for c in COND_ORDER if c in rows]

        # 1) recall@k grouped bars with 95% CI at each k
        fig, ax = plt.subplots(figsize=(9, 5))
        x = np.arange(len(k_values))
        w = 0.8 / max(1, len(conds))
        csv_rows = []
        for i, c in enumerate(conds):
            r = rows[c]
            vals = [r["recall_at_k"][str(k)] for k in k_values]
            cis = [r["recall_at_k_ci95"][str(k)] for k in k_values]
            errs = [[v - lo for v, (lo, hi) in zip(vals, cis)],
                    [hi - v for v, (lo, hi) in zip(vals, cis)]]
            ax.bar(x + i * w, vals, w, yerr=errs, capsize=2,
                   label=c, color=PALETTE[i % len(PALETTE)])
            for k, v, (lo, hi) in zip(k_values, vals, cis):
                csv_rows.append([c, k, v, lo, hi])
        ax.set_xticks(x + w * (len(conds) - 1) / 2)
        ax.set_xticklabels([f"@{k}" for k in k_values])
        ax.set_ylabel("Recall@k (hybrid, any-overlap)")
        ax.set_title(f"Recall@k by condition — Track {track}")
        ax.legend(fontsize=8, ncol=2)
        ax.set_ylim(0, 1.05)
        _save(fig, f"recall_at_k_by_condition_{track}")
        _csv(f"recall_at_k_by_condition_{track}", ["condition", "k", "recall", "ci_lo", "ci_hi"], csv_rows)

        # 2) dense vs hybrid recall@5 (H2 guardrail)
        fig, ax = plt.subplots(figsize=(9, 4.5))
        x = np.arange(len(conds))
        dense = [rows[c]["dense"]["recall_at_k"]["5"] for c in conds]
        hyb = [rows[c]["hybrid"]["recall_at_k"]["5"] for c in conds]
        ax.bar(x - 0.2, dense, 0.4, label="dense", color=PALETTE[0])
        ax.bar(x + 0.2, hyb, 0.4, label="hybrid (RRF)", color=PALETTE[1])
        ax.set_xticks(x); ax.set_xticklabels(conds, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Recall@5"); ax.set_ylim(0, 1.05)
        ax.set_title(f"Dense vs Hybrid recall@5 (H2 guardrail) — Track {track}")
        ax.legend()
        _save(fig, f"dense_vs_hybrid_{track}")
        _csv(f"dense_vs_hybrid_{track}", ["condition", "dense@5", "hybrid@5"],
             [[c, d, h] for c, d, h in zip(conds, dense, hyb)])

        # 3) ablation contributions
        abls = [r for r in results_json["ablation_contributions"] if r["track"] == track]
        if abls:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            names = [a["operation"] for a in abls]
            deltas = [a["delta_recall@5"] for a in abls]
            ax.barh(names, deltas, color=PALETTE[2])
            ax.axvline(0, color="#333", lw=0.8)
            ax.set_xlabel("Δ recall@5 (C3 − ablation)")
            ax.set_title(f"Ablation contributions — Track {track}")
            _save(fig, f"ablation_contributions_{track}")
            _csv(f"ablation_contributions_{track}", ["operation", "delta_recall@5"],
                 [[n, d] for n, d in zip(names, deltas)])

    # 4) faithfulness by condition (first track)
    b0 = bundles[0]
    fb = b0["faithfulness"].get("by_condition", {})
    if fb:
        fig, ax = plt.subplots(figsize=(7, 4))
        conds = [c for c in COND_ORDER if c in fb]
        ax.bar(conds, [fb[c] for c in conds], color=PALETTE[3])
        ax.set_ylabel("Faithfulness (0–1)"); ax.set_ylim(0, 1.05)
        ax.set_title(f"End-to-end faithfulness — Track {b0['track']}")
        _save(fig, "faithfulness_by_condition")
        _csv("faithfulness_by_condition", ["condition", "faithfulness"],
             [[c, fb[c]] for c in conds])

    # 5) cost vs recall scatter (fresh+cached LLM tokens)
    fig, ax = plt.subplots(figsize=(7, 5))
    for b in bundles:
        rows = _rows_for(results_json, b["track"])
        for i, c in enumerate([c for c in COND_ORDER if c in rows]):
            r = rows[c]
            toks = r["cost"].get("fresh_tokens", 0) + r["cost"].get("cached_tokens", 0)
            cost = toks or (r["cost"]["format_seconds"] + r["cost"]["index_seconds"])
            ax.scatter(cost, r["recall_at_k"]["5"], color=PALETTE[i % len(PALETTE)], s=60)
            ax.annotate(c, (cost, r["recall_at_k"]["5"]), fontsize=7,
                        xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("cost per method (fresh+cached LLM tokens, or seconds if no LLM)")
    ax.set_ylabel("Recall@5"); ax.set_title("Cost vs recall@5")
    _save(fig, "cost_vs_recall")

    # 6) composition figure (C0 vs C4, C2 vs C5) + common-size control CSV (v1.1 §7)
    tm_by_track = {t["track"]: t for t in results_json.get("tracks_meta", [])}
    for b in bundles:
        track = b["track"]
        rows = _rows_for(results_json, track)
        pairs = [("C0", "C4"), ("C2", "C5")]
        have = [(a, c) for a, c in pairs if a in rows and c in rows]
        if have:
            fig, ax = plt.subplots(figsize=(7, 4.5))
            x = np.arange(len(have))
            base = [rows[a]["recall_at_k"]["5"] for a, _ in have]
            comp = [rows[c]["recall_at_k"]["5"] for _, c in have]
            base_ci = [rows[a]["recall_at_k_ci95"]["5"] for a, _ in have]
            comp_ci = [rows[c]["recall_at_k_ci95"]["5"] for _, c in have]
            be = [[v - lo for v, (lo, hi) in zip(base, base_ci)], [hi - v for v, (lo, hi) in zip(base, base_ci)]]
            ce = [[v - lo for v, (lo, hi) in zip(comp, comp_ci)], [hi - v for v, (lo, hi) in zip(comp, comp_ci)]]
            ax.bar(x - 0.2, base, 0.4, yerr=be, capsize=3, label="baseline", color=PALETTE[0])
            ax.bar(x + 0.2, comp, 0.4, yerr=ce, capsize=3, label="+ formatted", color=PALETTE[2])
            ax.set_xticks(x); ax.set_xticklabels([f"{a}→{c}" for a, c in have])
            ax.set_ylabel("Recall@5"); ax.set_ylim(0, 1.05)
            ax.set_title(f"Composition / H4 — Track {track}")
            ax.legend()
            _save(fig, f"composition_{track}")
        cs = tm_by_track.get(track, {}).get("common_size", {})
        if cs and "original_256" in cs:
            _csv(f"common_size_control_{track}", ["variant", "recall@5_at_256"],
                 [["original", cs.get("original_256")], ["formatted", cs.get("formatted_256")]])


# --------------------------------------------------------------------------
# results.md
# --------------------------------------------------------------------------
def _write_markdown(results_json, bundles, cfg) -> None:
    v = results_json["verdict"]
    L = []
    L.append("# RAG Semantic Formatter — Results\n")
    L.append(f"**Run:** `{results_json['run_id']}` · **UTC:** {results_json['created_utc']} · "
             f"**config digest:** `{results_json['config_digest'][:12]}…`\n")

    # TL;DR
    L.append("## TL;DR verdict\n")
    comp = " · **COMPLEMENT**" if v.get("complement") else ""
    L.append(f"**Decision: {v['decision']}**{comp} — H1 {v['H1']}, H2 {v['H2']}, H3 {v['H3']}, "
             f"H4 {v.get('H4', 'n/a')}.\n")
    L.append(f"> {v['notes']}\n")
    prov = results_json["environment"]["llm_provider"]
    backend = results_json["environment"]["embedding_backend"]
    if prov == "none" or backend == "hash":
        L.append(f"\n> ⚠️ **Provenance of these numbers:** llm.provider=`{prov}`, "
                 f"embedding backend=`{backend}`. C2 blurbs / C3 edits use the labeled "
                 f"rule-based stubs and (if backend=hash) embeddings are lexical only. "
                 f"Treat as a pipeline/mechanism check, not the headline paid run.\n")

    # Setup
    L.append("\n## Setup\n")
    env = results_json["environment"]
    L.append(f"- Tracks: {', '.join(results_json['tracks'])}; conditions: "
             f"{', '.join(results_json['conditions'])}.")
    L.append(f"- Embedding: `{env['embedding_model']}` (backend `{env['embedding_backend']}`, "
             f"rev `{env['embedding_revision']}`); FAISS `{env['faiss']}`; seed {env['seed']}.")
    L.append(f"- LLM: `{env['llm_model']}` (provider `{env['llm_provider']}`).")
    L.append(f"- Chosen chunk sizes (dev-swept, §5.3): {results_json['chosen_chunk_sizes']}.")
    for b in bundles:
        L.append(f"- Track {b['track']}: n_test={b['n_test']} queries.")

    # Headline table per track
    for b in bundles:
        track = b["track"]
        rows = _rows_for(results_json, track)
        L.append(f"\n## Headline — Track {track} (recall@k, hybrid, any-overlap; 95% CI at k=5)\n")
        L.append("| Condition | R@1 | R@3 | R@5 [CI] | R@10 | nDCG@5 | MRR | units | u/doc |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for c in [c for c in COND_ORDER if c in rows]:
            r = rows[c]
            ci = r["recall_at_k_ci95"]["5"]
            cs = r["chunk_stats"]
            L.append(f"| {c} | {r['recall_at_k']['1']:.3f} | {r['recall_at_k']['3']:.3f} | "
                     f"{r['recall_at_k']['5']:.3f} [{ci[0]:.3f},{ci[1]:.3f}] | "
                     f"{r['recall_at_k']['10']:.3f} | {r['ndcg_at_k'].get('5', 0):.3f} | {r['mrr']:.3f} | "
                     f"{cs['index_units']} | {cs['units_per_doc_mean']:.1f} |")
        L.append(f"\n![recall](figures/recall_at_k_by_condition_{track}.svg)\n")

        # pairwise
        pw = [p for p in results_json["pairwise"] if p["track"] == track]
        if pw:
            L.append(f"\n### Significance (paired bootstrap + permutation, Holm) — Track {track}\n")
            L.append("| Pair | Δrecall@5 | 95% CI | p | p(Holm) | CI excludes 0 |")
            L.append("|---|---|---|---|---|---|")
            for p in pw:
                L.append(f"| {p['pair']} | {p['mean_diff']:+.3f} | "
                         f"[{p['ci95'][0]:+.3f},{p['ci95'][1]:+.3f}] | {p['p_value']:.4f} | "
                         f"{p.get('p_holm', float('nan')):.4f} | {'yes' if p['significant'] else 'no'} |")

        # Composition / H4 + common-size control
        tm = next((t for t in results_json.get("tracks_meta", []) if t["track"] == track), {})
        cs = tm.get("common_size", {})
        if "C4" in rows or "C5" in rows:
            L.append(f"\n### Composition / complementarity (H4) — Track {track}\n")
            if "C4" in rows and "C0" in rows:
                L.append(f"- C4 (formatted+naive) {rows['C4']['recall_at_k']['5']:.3f} vs "
                         f"C0 (naive) {rows['C0']['recall_at_k']['5']:.3f}.")
            if "C5" in rows and "C2" in rows:
                L.append(f"- C5 (formatted+contextual) {rows['C5']['recall_at_k']['5']:.3f} vs "
                         f"C2 (contextual) {rows['C2']['recall_at_k']['5']:.3f} — the H4 test.")
            L.append(f"\n![composition](figures/composition_{track}.svg)\n")
        if cs.get("original_256") is not None:
            L.append(f"\n**Common-size control (naive @256, §5.2):** original corpus "
                     f"{cs['original_256']:.3f} vs formatted corpus {cs['formatted_256']:.3f} "
                     f"(Δ={cs['formatted_256'] - cs['original_256']:+.3f}) — isolates text-quality "
                     f"from unit-count. See `figures/common_size_control_{track}.csv`.\n")

    # Guardrail
    L.append("\n## Guardrail — dense vs hybrid (H2)\n")
    L.append("Vocabulary drift would show as hybrid failing to track dense. See "
             "`figures/dense_vs_hybrid_<track>.svg`. "
             f"Preserved-term failures: {results_json['readability']['preserved_term_failures']}.\n")

    # Diagnostics (v1.1 §8)
    L.append("\n## Diagnostics (§8)\n")
    for b in bundles:
        track = b["track"]
        rows = _rows_for(results_json, track)
        if "C2" in rows and "C0" in rows:
            c2d = rows["C2"]["dense"]["recall_at_k"]["5"]
            c0d = rows["C0"]["dense"]["recall_at_k"]["5"]
            c2h = rows["C2"]["recall_at_k"]["5"]
            c0h = rows["C0"]["recall_at_k"]["5"]
            same = abs(c2d - c0d) < 1e-4
            L.append(f"- **§8a C2-dense vs C0-dense (Track {track}):** dense C2={c2d:.4f} vs "
                     f"C0={c0d:.4f} ({'identical' if same else 'differ'}); hybrid C2={c2h:.3f} vs "
                     f"C0={c0h:.3f}. "
                     + ("The blurb barely moves DENSE ranking (blurb is small relative to a "
                        "768-token unit) but lifts HYBRID via BM25 — the gain is lexical, not "
                        "semantic. Not a bug: the blurbed text is what gets embedded (see "
                        "ContextualChunker), the dense delta is just negligible at this unit size."
                        if same else "Blurbs moved dense ranking as expected."))
        if "C1" in rows:
            cs = rows["C1"]["chunk_stats"]
            L.append(f"- **§8b C1 semantic sanity (Track {track}):** {cs['index_units']} units, "
                     f"{cs['units_per_doc_mean']:.1f}/doc, mean {cs['token_mean']:.0f} tokens. "
                     "See `results.md` diagnostics note / boundary dump in the run log.")
        # §8c corrected nosize contribution
        nos = next((a for a in results_json["ablation_contributions"]
                    if a["track"] == track and a["operation"] == "right_sizing"), None)
        if nos and "C3-nosize" in rows:
            L.append(f"- **§8c nosize floor (Track {track}):** with the ≥30-token unit floor, "
                     f"C3-nosize has {rows['C3-nosize']['chunk_stats']['index_units']} units "
                     f"(was ~5,143 degenerate micro-units in v1.0); corrected right-sizing "
                     f"contribution Δrecall@5={nos['delta_recall@5']:+.3f}.")

    # Reranking axis (amendment v1.3, H6)
    rr = results_json.get("rerank", {})
    if rr.get("enabled"):
        model = rr.get("config", {}).get("model", "?")
        L.append("\n## Reranking axis (amendment v1.3, H6)\n")
        L.append(f"Cross-encoder `{model}` reranking the fused candidate pool before the "
                 "top-k cut. Orthogonal axis: every condition is scored with and without "
                 "reranking from the same retrieval call, paired over queries.\n")
        me = rr.get("main_effect", [])
        if me:
            L.append("### H6 main effect — recall@5 (hybrid, any)\n")
            L.append("| Track | Condition | base | +rerank | Δ | 95% CI | p | p(Holm) | "
                     "CI excludes 0 |")
            L.append("|---|---|---|---|---|---|---|---|---|")
            for r in me:
                L.append(f"| {r['track']} | {r['condition']} | {r['base']:.3f} | "
                         f"{r['reranked']:.3f} | {r['mean_diff']:+.4f} | "
                         f"[{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] | {r['p_value']:.4f} | "
                         f"{r.get('p_holm', float('nan')):.4f} | "
                         f"{'yes' if r['significant'] else 'no'} |")
            L.append("")
        for it in rr.get("interaction", []):
            L.append(f"### H6a interaction — Track {it['track']}\n")
            L.append(f"- formatter gain (C3 − C0): **{it['formatter_gain_c3_vs_c0']:+.4f}**")
            L.append(f"- rerank gain on C0: **{it['rerank_gain_on_c0']:+.4f}**")
            L.append(f"- rerank gain on C3: **{it['rerank_gain_on_c3']:+.4f}**")
            L.append(f"- difference-in-differences `{it['quantity']}`: **{it['did']:+.4f}**, "
                     f"95% CI [{it['ci95'][0]:+.4f}, {it['ci95'][1]:+.4f}], "
                     f"p={it['p_value']:.4f}")
            L.append(f"- reading: **{it['reading']}**")
            c0rr = it.get("c0_plus_rerank_vs_c3", {})
            if c0rr:
                L.append(f"- H6b, C0+rerank vs C3: {c0rr['mean_diff']:+.4f} "
                         f"[{c0rr['ci95'][0]:+.4f}, {c0rr['ci95'][1]:+.4f}], "
                         f"{'significant' if c0rr['significant'] else 'not significant'}")
            L.append("")

    # Ablations
    if results_json["ablation_contributions"]:
        L.append("\n## Ablations (Δrecall@5 = C3 − ablation)\n")
        L.append("| Track | Operation | Δrecall@5 |")
        L.append("|---|---|---|")
        for a in results_json["ablation_contributions"]:
            L.append(f"| {a['track']} | {a['operation']} | {a['delta_recall@5']:+.3f} |")
        L.append("\n`text_editing_vs_markers` isolates the value of editing text over pure "
                 "boundary markers (§9).\n")

    # Faithfulness
    fb = bundles[0]["faithfulness"].get("by_condition", {})
    if fb:
        L.append("\n## Faithfulness\n")
        L.append(f"Rubric: {bundles[0]['faithfulness'].get('rubric','')}. "
                 f"By condition (0–1): " + ", ".join(f"{k}={x:.3f}" for k, x in fb.items()) + ".\n")
        L.append("![faithfulness](figures/faithfulness_by_condition.svg)\n")

    # Cost
    L.append("\n## Cost\n")
    L.append(f"LLM cost (global): {bundles[0]['llm_cost']}. See `figures/cost_vs_recall.svg`.\n")

    # Readability
    rd = results_json["readability"]
    L.append("\n## Readability (H3)\n")
    L.append(f"C3 mean {rd['c3_mean']:.2f} vs original {rd['original_mean']:.2f} on "
             f"{rd['n_docs']} docs; preserved-term failures {rd['preserved_term_failures']}. "
             f"Rubric: {rd['rubric']}.\n")

    # Threats
    L.append("\n## Threats to validity\n")
    L.append("- **Track A is synthetic and adversarial by construction** — the injected damage "
             "(anaphora, duplication, split) is exactly what the formatter targets, so Track A "
             "shows *mechanism*, not field generalization. VALIDATE requires ≥2 tracks (§2.4).")
    if env["llm_provider"] == "none":
        L.append("- **provider=none**: C2/C3 use rule-based stubs; the LLM formatter/blurbs are "
                 "not exercised. Re-run with `--provider anthropic` for the headline result.")
    if env["embedding_backend"] == "hash":
        L.append("- **hash embedding backend**: dense retrieval is lexical, not semantic; "
                 "rerun with `sentence-transformers` for meaningful dense numbers.")
    L.append("- **Per-condition LLM cost attribution** is approximate; only C2/C3 are charged "
             "and the global tally is authoritative.")
    L.append("- **Formatter provenance is approximate** (edited units map to source sentence "
             "offsets); any/strict variants are both reported as a cross-check (§13).")

    # Reproduction
    L.append("\n## Reproduction\n")
    L.append("```bash\nmake setup\nmake test\npython -m src.run --track A --provider none  # zero-cost\n"
             "python -m src.run --track A --provider anthropic   # headline (needs ANTHROPIC_API_KEY)\n"
             "python -m src.run --report-only\n```\n")
    L.append(f"Pre-registration hash: `{results_json['preregistration_hash'][:16]}…` "
             "(frozen before treatment metrics).\n")

    (RESULTS / "results.md").write_text("\n".join(L), encoding="utf-8")


# --------------------------------------------------------------------------
class _LiteResult:
    """Adapter exposing the attributes figures/markdown read, from stored aggregates."""
    def __init__(self, cost_row):
        self._cost = cost_row


def _pseudo_bundles(rj: dict) -> list[dict]:
    """Reconstruct the minimal bundle view figures/markdown need, from results.json."""
    bundles = []
    for tm in rj.get("tracks_meta", []):
        track = tm["track"]
        cond_ids = [r["condition"] for r in rj["results"]
                    if r["track"] == track and r["overlap_variant"] == "any"]
        bundles.append({
            "track": track, "n_test": tm["n_test"],
            "faithfulness": tm["faithfulness"], "llm_cost": tm["llm_cost"],
            "readability": tm["readability"],
            "results": {cid: None for cid in dict.fromkeys(cond_ids)},
            "pairwise": [p for p in rj["pairwise"] if p["track"] == track],
            "ablations": [a for a in rj["ablation_contributions"] if a["track"] == track],
        })
    return bundles


def rebuild() -> None:
    """Regenerate figures + markdown from the last results.json (aggregates only)."""
    rj = json.loads((RESULTS / "results.json").read_text(encoding="utf-8"))
    if "tracks_meta" not in rj:
        raise RuntimeError("results.json predates tracks_meta; re-run `python -m src.run`.")
    bundles = _pseudo_bundles(rj)
    _write_figures(rj, bundles)
    _write_markdown(rj, bundles, {"seed": rj["environment"].get("seed", 0)})


def _py_version():
    import platform
    return platform.python_version()


def _os_string():
    import platform
    return f"{platform.system()} {platform.release()}"


def _pkg_version(name):
    try:
        import importlib.metadata as m
        return m.version(name if name != "faiss" else "faiss-cpu")
    except Exception:
        return "?"
