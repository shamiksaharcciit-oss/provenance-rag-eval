"""PW-1 interpretation rule, in code (work order A7 + A2).

The five-branch rule and the retention ratio are frozen in
`posthoc_PW1_provenance_width.json`. This is the executable form, so the classification is
computed by the rule rather than by a human reading a table against it.

**`r <= 1.0` is a HALT, not a reported value.** Removing ranges can only turn a hit into a miss,
never the reverse, and the unformatted arm has nothing to strip (its width is exactly 1.0000).
So `delta_S2 <= delta_full` by construction, and `r > 1` is a defect in the scoring — most
likely ranges being added rather than removed, or a mismatched cell pairing. A structural
invariant checked only by a human reading a table is not checked. Same tier as NC-A/NC-B: it
stops the run.
"""
from __future__ import annotations

from src.stats.tests import holm_correction

R_SEPARATED = 0.75
R_NOT_SEPARATED = 0.25
ALPHA = 0.05
R_TOLERANCE = 1e-9   # floating-point slack only; NOT a tolerance for real overshoot


class RatioExceedsOne(AssertionError):
    """`r > 1`: the corrected estimate exceeds the published one. Structurally impossible.

    Stripping ranges is monotone in hits, so the corrected delta cannot exceed the published
    delta. Raised rather than reported, because a number that cannot occur is evidence of a
    defect in the scoring, not a finding about the corpus.
    """


class BoundaryZeroCI(ValueError):
    """A CI bound of exactly 0.0 is ambiguous unless the rule says which way it falls."""


def excludes_zero(ci: tuple[float, float]) -> bool:
    """Frozen boundary rule: a CI whose bound is exactly 0.0 does NOT exclude zero."""
    lo, hi = ci
    return lo > 0.0 or hi < 0.0


def retention_ratio(delta_corrected: float, delta_full: float) -> float:
    """`r = delta_corrected / delta_full`, sign retained, with the A7 halt."""
    if delta_full == 0.0:
        raise ZeroDivisionError("delta_full is 0.0; the cell cannot be applicable (branch 1)")
    r = delta_corrected / delta_full
    if r > 1.0 + R_TOLERANCE:
        raise RatioExceedsOne(
            f"r = {r:.6f} > 1: corrected delta {delta_corrected:+.6f} exceeds published "
            f"{delta_full:+.6f}. Stripping ranges is monotone in hits and the unformatted arm "
            f"has nothing to strip, so this cannot happen. Check that the scoring REMOVES "
            f"ranges, and that the cell pairing is correct."
        )
    return r


def classify_cell(*, delta_full: float, full_significant: bool,
                  delta_corrected: float, ci_corrected: tuple[float, float],
                  p_holm_corrected: float) -> dict:
    """The frozen five-branch rule, evaluated in order, first match wins.

    `full_significant` is supplied by the caller and must be computed under
    `branch_1_significance` = Holm WITHIN THE DECLARED PW-1 FAMILY. It is never the stored
    `p_holm` from a published run: those are Holm over that run's own six-member pairwise
    family, which is not a PW-1 family and would import a foreign multiplicity.
    """
    if not full_significant:
        r = None if delta_full == 0.0 else delta_corrected / delta_full
        return {"branch": "NOT APPLICABLE", "r": r,
                "why": "delta_full is not significant under branch_1_significance; there is no "
                       "effect to separate. r is descriptive only."}

    r = retention_ratio(delta_corrected, delta_full)   # A7 halt lives here

    lo, hi = ci_corrected
    if lo <= delta_full <= hi and not excludes_zero(ci_corrected):
        return {"branch": "UNDERPOWERED", "r": r,
                "why": "the corrected CI contains both zero and delta_full, so it cannot "
                       "discriminate between the effect being intact and being gone."}
    if r < R_NOT_SEPARATED or not excludes_zero(ci_corrected):
        return {"branch": "NOT SEPARATED", "r": r,
                "why": f"r = {r:.4f} < {R_NOT_SEPARATED}" if r < R_NOT_SEPARATED
                       else "the corrected CI contains zero."}
    if r >= R_SEPARATED and p_holm_corrected < ALPHA:
        return {"branch": "SEPARATED", "r": r,
                "why": f"r = {r:.4f} >= {R_SEPARATED} and the cell remains significant after "
                       f"Holm within the corrected family (p_holm = {p_holm_corrected:.6g})."}
    return {"branch": "PARTIALLY SEPARATED", "r": r,
            "why": f"r = {r:.4f} with p_holm = {p_holm_corrected:.6g} — neither band."}


_ORDER = {"NOT SEPARATED": 0, "PARTIALLY SEPARATED": 1, "SEPARATED": 2}


def aggregate(labels: list[str]) -> str:
    """Least favourable label among applicable and powered cells, per family."""
    scored = [l for l in labels if l in _ORDER]
    if not scored:
        return "UNDERPOWERED"
    return min(scored, key=lambda l: _ORDER[l])


def holm_within_family(pvals: list[float]) -> list[float]:
    """Holm over a PW-1 family only. Named so no published `p_holm` is used by mistake."""
    return holm_correction(pvals)
