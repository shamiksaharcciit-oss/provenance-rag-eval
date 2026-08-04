"""v1.11 §6 — request construction for E-A, E-B, E-C, E-E.

Every package this module builds is returned alongside its text, because PF-G1 promoted
"persist every package text" from advice to requirement and a builder that returns only ids
makes the acceptor unsatisfiable.

Budgets follow the frozen procedures exactly:

  * E-A, E-B, E-C use `b2_for_query` over the **three v1.9 arms**, which is the budget v1.9's
    packages were built at — E-B and E-C are re-runs of v1.9's packages under a new model and
    new prompts, so their packages must be v1.9's.
  * E-E takes B2(q) over **its own pair** (`C768`, `U768`), per §5, and its `U768` packages are
    therefore NOT comparable to v1.9's. The plan requires that stated in the table header.
"""
from __future__ import annotations

from src.textutil import count_tokens
from v19.arms import build_inventories, test_queries
from v19.control import b2_for_query
from v19.packages import build_all
from v110.arms import build_contextual
from v111.ids import custom_id
from v111.prompts import render
from v111.unanswerable import assert_no_gold_overlap, same_doc_answerless

V19_ARMS = ("F768", "U768", "U256")
C2_PARAMS = {"base": "naive", "chunk_tokens": 768, "overlap_frac": 0.0, "blurb_max_sentences": 2}


def load_track_a():
    """Inventories, queries, and the C768 arm. Cache-only: no formatter call may spend."""
    from src.chunkers.base import ChunkContext
    from src.llm.client import build_llm

    ds, tcfg, built = build_inventories("A")
    _dev, test = test_queries(ds, tcfg, "A")
    invs = {a: built[a][0] for a in V19_ARMS}
    ctx = ChunkContext(embedder=None, llm=build_llm(tcfg), config=tcfg)
    invs["C768"] = build_contextual(ds, ctx, C2_PARAMS)
    return ds, tcfg, invs, test


def v19_packages(invs, q):
    """The frozen v1.9 packages for one query, rebuilt (PF-G1: v1.9 never persisted them)."""
    b = b2_for_query({a: invs[a] for a in V19_ARMS}, q.gold_spans)
    built = build_all({a: invs[a] for a in V19_ARMS}, q.gold_spans, b["b2"])
    return b, {a: built["packages"][a].package.text for a in V19_ARMS}


def ee_packages(invs, q):
    """§5: B2(q) over the C768/U768 pair alone. Not v1.9's budgets, by design."""
    pair = {"C768": invs["C768"], "U768": invs["U768"]}
    b = b2_for_query(pair, q.gold_spans)
    built = build_all(pair, q.gold_spans, b["b2"])
    return b, {a: built["packages"][a].package.text for a in pair}


def build_all_specs(invs, test):
    """Every request for every stage, with its package text. Returns (specs, packages).

    `specs` entries are `{custom_id, prompt, system, stage, exp, arm, variant, query_id}`;
    `packages` maps `custom_id -> package text` so the persistence acceptor can be satisfied
    from the same object that produced the request.
    """
    specs, packages, gaps = [], {}, []
    n = len(test)
    succ = [test[(i + 1) % n].query_id for i in range(n)]
    by_id = {q.query_id: q for q in test}

    for i, q in enumerate(test):
        b19, p19 = v19_packages(invs, q)

        # ---- E-A cross-doc: the successor query's package for the same arm
        sq = by_id[succ[i]]
        _bs, ps = v19_packages(invs, sq)
        for arm in ("F768", "U768"):
            cid = custom_id("ea", arm.lower(), i, "xdoc")
            packages[cid] = ps[arm]
            specs.append({"custom_id": cid, "prompt": render("frozen", ps[arm], q.text),
                          "system": "", "stage": "ea", "exp": "ea", "arm": arm,
                          "variant": "xdoc", "query_id": q.query_id,
                          "package_of": sq.query_id})

        # ---- E-A same-doc: gold-bearing units excluded; may be unconstructible (the six)
        for arm in ("F768", "U768"):
            units = same_doc_answerless(invs[arm], q.gold_spans, b19["b2"])
            if units is None:
                gaps.append({"query_id": q.query_id, "arm": arm,
                             "reason": "no non-gold unit in the gold document"})
                continue
            assert_no_gold_overlap(units, q.gold_spans, f"{q.query_id}/{arm}")
            text = "\n\n".join(u.text for u in units)
            cid = custom_id("ea", arm.lower(), i, "sdoc")
            packages[cid] = text
            specs.append({"custom_id": cid, "prompt": render("frozen", text, q.text),
                          "system": "", "stage": "ea", "exp": "ea", "arm": arm,
                          "variant": "sdoc", "query_id": q.query_id,
                          "package_tokens": count_tokens(text)})

        # ---- E-B: v1.9's packages, Haiku, frozen prompt
        for arm in ("F768", "U768"):
            cid = custom_id("eb", arm.lower(), i, "frozen")
            packages[cid] = p19[arm]
            specs.append({"custom_id": cid, "prompt": render("frozen", p19[arm], q.text),
                          "system": "", "stage": "eb", "exp": "eb", "arm": arm,
                          "variant": "frozen", "query_id": q.query_id})

        # ---- E-C: v1.9's packages, Sonnet, two prompt variants
        for variant in ("v1", "v2"):
            for arm in ("F768", "U768"):
                cid = custom_id("ec", arm.lower(), i, variant)
                packages[cid] = p19[arm]
                specs.append({"custom_id": cid, "prompt": render(variant, p19[arm], q.text),
                              "system": "", "stage": f"ec-{variant}", "exp": "ec", "arm": arm,
                              "variant": variant, "query_id": q.query_id})

        # ---- E-E: C768 vs U768 at this pair's own budget
        _be, pe = ee_packages(invs, q)
        for arm in ("C768", "U768"):
            cid = custom_id("ee", arm.lower(), i, "frozen")
            packages[cid] = pe[arm]
            specs.append({"custom_id": cid, "prompt": render("frozen", pe[arm], q.text),
                          "system": "", "stage": "ee", "exp": "ee", "arm": arm,
                          "variant": "frozen", "query_id": q.query_id})

    return specs, packages, gaps
