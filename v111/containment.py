"""v1.11 §4 — E-D, the containment re-score. CODE ONLY, ZERO CALLS.

PR-2 failed: `F768` scored lower on exact containment than `U768` while token-F1 ran the other
way. The Gate 1 §2 HYPOTHESIS was that containment measures verbatim fidelity against the
ORIGINAL span text, while `F768`'s packages carry FORMATTED text the treatment is permitted to
edit — so a faithful quote of formatted text can fail containment against the original.

This recomputes containment for the EXISTING v1.9 answers against the package text each arm
actually showed the model, beside the already-reported original-text containment. The procedure
is frozen here before any value is seen. Descriptive: two tables side by side, no test.

Support is directional and stated in advance: `F768` containment rises against its own text
while `U768`'s stays stable. Anything else kills the hypothesis.
"""
from __future__ import annotations

from src.v17.reading import exact_containment, normalise


def containment_against(answer: str, reference_text: str) -> int:
    """1 iff the normalised answer appears in the normalised reference. Frozen normalisation."""
    a, r = normalise(answer), normalise(reference_text)
    return 1 if a and a in r else 0


def rescore(rows: list[dict], gold_by_q: dict, package_by_q_arm: dict, arms=("F768", "U768")):
    """Both containment readings per arm. `rows` are v1.9's persisted answers."""
    out = {a: {"vs_original_gold": 0, "vs_package_text": 0, "n": 0} for a in arms}
    for r in rows:
        q = r["query_id"]
        for a in arms:
            ans = r["arms"][a]["answer"]
            out[a]["n"] += 1
            out[a]["vs_original_gold"] += exact_containment(ans, gold_by_q[q])
            pkg = package_by_q_arm.get((q, a))
            if pkg is not None:
                out[a]["vs_package_text"] += containment_against(ans, pkg)
    return out
