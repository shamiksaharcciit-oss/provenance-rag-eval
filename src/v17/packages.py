"""v1.7 E2 — oracle package construction (plan §3.1).

Retrieval is removed by construction: the gold-bearing units are selected directly, then padded
with their neighbours to a fixed token budget. Both arms hand the generator the same number of
tokens containing the same gold information, so the only difference is packaging.

NOTHING HERE CALLS A MODEL. Building a package is deterministic and free; E2 is gated on E1 and
this module runs under test at Gate 0 so the construction is frozen before any generation.

DECLARED READINGS, fixed before any v17 value exists. Each is a point where §3.1's prose admits
more than one implementation, and each is stated rather than chosen silently:

  * "Minimal set of the arm's units whose source_ranges overlap G(q)" is read as exactly the set
    of units with non-zero overlap — no proper subset can contain all gold, so that set is
    already minimal, and no search is performed.
  * Padding never crosses a document. Gold spans of one query all lie in one document (measured
    at Gate 0: zero multi-document gold queries in either track), and `PaddingUnsupported` fires
    rather than inventing a cross-document order if that ever changes.
  * "Truncate the final unit" is read as the LAST UNIT ADDED — the one that carried the package
    past B2 — and it is truncated at its far end, the end away from the gold material. A
    following unit loses its tail; a preceding unit loses its head. This keeps the surviving text
    contiguous with the gold rather than leaving a hole beside it, and it never shortens a unit
    added earlier.
  * Units are joined with a blank line, identically for every arm. §3.1 forbids markers, headers
    and annotations; some separator must exist or adjacent units weld into one word, and a blank
    line is the one choice that adds no token to either arm (`count_tokens` counts word and
    punctuation runs, never whitespace) and so cannot shift the budget between them.

THE BUDGET IS PER QUERY, NOT GLOBAL (plan §3.1, pre-freeze amendment PF-2).

    B2(q) = max(1024, T_a(q) over every arm a included in E2 on that track)

where `T_a(q)` is the token length of arm `a`'s minimal gold-covering unit set. Every arm's
package for query `q` is built to exactly B2(q). The guarantee the design needs is equal tokens
WITHIN EACH PAIR, because the comparison is paired per query; a global constant was a stronger
condition than the comparison ever required, and at 1024 it was one the corpus refutes — the
gold-bearing run exceeds it on 6/176 Track A `U768` queries and on 61/150 Track B.

B2(q) is deterministic from the frozen inventories, symmetric across arms, fixed before any
generation and outcome-independent: the budget is set by rule, not by result.

`GoldExceedsBudget` is retained as an assertion against B2(q), where it is unreachable by
construction — B2(q) is at least the gold-covering set's own length. If it ever raises, that is
an APPARATUS-STOP, which is why it was kept rather than deleted once it stopped being reachable.
`B2_CAP` is the second stop: nothing known approaches 8192, so exceeding it means diagnose, not
accommodate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.chunkers.base import Unit
from src.datasets.base import GoldSpan
from src.textutil import _TOKEN_RE, count_tokens

JOIN = "\n\n"
B2_FLOOR = 1024
B2_CAP = 8192


class PaddingUnsupported(AssertionError):
    """The package cannot be built as specified. Stop and report; do not approximate."""


class GoldExceedsBudget(PaddingUnsupported):
    """The gold-bearing units alone exceed the budget, so landing on it would truncate gold.

    Unreachable once the budget is B2(q). Retained so that reaching it is an APPARATUS-STOP.
    """


class BudgetCapExceeded(PaddingUnsupported):
    """B2(q) exceeded `B2_CAP`. Diagnose; do not accommodate."""


@dataclass
class MatchedBudget:
    b2: int
    set_by: list[str]           # arms whose T_a(q) determined it; empty when the floor governs
    costs: dict[str, int]       # T_a(q) per arm, descriptive
    escalated: bool             # True iff the floor did not govern


def matched_budget(inventories: dict[str, list[Unit]], gold: list[GoldSpan],
                   floor: int = B2_FLOOR, cap: int = B2_CAP) -> MatchedBudget:
    """B2(q) = max(floor, T_a(q) over every arm), per plan §3.1 (PF-2).

    `inventories` maps arm id to that arm's units. Every arm included in E2 on the track must be
    present: an arm left out cannot raise the budget, and a budget that does not clear an arm's
    gold is the defect this rule exists to remove.
    """
    if not inventories:
        raise PaddingUnsupported("B2(q) is undefined with no arms")
    costs = {}
    for arm, units in inventories.items():
        t = gold_token_cost(units, gold)
        if t < 0:
            raise PaddingUnsupported(
                f"arm {arm}: no single-document gold-covering unit set, so T_a(q) is undefined")
        costs[arm] = t
    peak = max(costs.values())
    b2 = max(floor, peak)
    if b2 > cap:
        raise BudgetCapExceeded(
            f"B2(q) = {b2} exceeds the cap {cap}; diagnose rather than accommodate (§3.1)")
    return MatchedBudget(b2=b2, costs=costs, escalated=peak > floor,
                         set_by=sorted(a for a, t in costs.items() if t == peak and peak > floor))


@dataclass
class Package:
    text: str
    tokens: int
    unit_ids: list[str]
    core_unit_ids: list[str]
    shortfall: int = 0
    truncated_unit_id: str | None = None
    meta: dict = field(default_factory=dict)


def _overlaps(unit: Unit, gold: list[GoldSpan]) -> bool:
    from src.score.provenance import covered_chars

    return any(covered_chars(unit, g) > 0 for g in gold)


def truncate_tokens(text: str, keep: int, from_start: bool) -> str:
    """Cut `text` to `keep` tokens at a token boundary.

    `from_start=True` keeps the head and drops the tail; `False` keeps the tail and drops the
    head. Slicing on token boundaries from the same regex `count_tokens` uses means the result's
    token count is exactly `keep`, which the caller asserts.
    """
    if keep <= 0:
        return ""
    spans = [(m.start(), m.end()) for m in _TOKEN_RE.finditer(text)]
    if keep >= len(spans):
        return text
    return text[: spans[keep - 1][1]] if from_start else text[spans[len(spans) - keep][0] :]


def build_package(units: list[Unit], gold: list[GoldSpan], budget_tokens: int) -> Package:
    """Build one oracle package. `units` is the arm's inventory in document order.

    Only units from the gold document participate; §3.1's "document order" is their order in
    `units`, which is the order the chunker emitted them.
    """
    docs = {g.doc_id for g in gold}
    if len(docs) != 1:
        raise PaddingUnsupported(
            f"gold spans {len(docs)} documents; §3.1's padding order is defined within a "
            f"document. Measured at Gate 0: no such query exists in either track.")
    doc_id = docs.pop()
    inv = [u for u in units if u.doc_id == doc_id]
    core_ix = [i for i, u in enumerate(inv) if _overlaps(u, gold)]
    if not core_ix:
        raise PaddingUnsupported(
            "no unit overlaps the gold span — the arm's provenance does not cover its own "
            "corpus, which is an apparatus fault and not a package")

    lo, hi = min(core_ix), max(core_ix)
    chosen = list(range(lo, hi + 1))  # document order; interior non-overlapping units included
    total = sum(count_tokens(inv[i].text) for i in chosen)
    if total > budget_tokens:
        raise GoldExceedsBudget(
            f"gold-bearing units span {total} tokens > B2 {budget_tokens}; landing on B2 would "
            f"truncate gold, which §3.3 assumes impossible")

    # Alternate following, then preceding, per §3.1.
    nxt, prv, want_following, order = hi + 1, lo - 1, True, []
    while total < budget_tokens and (nxt < len(inv) or prv >= 0):
        if want_following and nxt < len(inv):
            i = nxt
            nxt += 1
        elif prv >= 0:
            i = prv
            prv -= 1
        else:
            i = nxt
            nxt += 1
        order.append(i)
        total += count_tokens(inv[i].text)
        want_following = not want_following

    chosen = sorted(set(chosen) | set(order))
    tokens = [count_tokens(inv[i].text) for i in chosen]
    truncated_id, shortfall = None, 0
    if sum(tokens) > budget_tokens:
        last = order[-1]
        over = sum(tokens) - budget_tokens
        pos = chosen.index(last)
        keep = tokens[pos] - over
        # far end = away from the core: a following unit keeps its head, a preceding unit its tail
        text = truncate_tokens(inv[last].text, keep, from_start=last > hi)
        assert count_tokens(text) == keep, "truncation missed the token boundary"
        pieces = [inv[i].text if i != last else text for i in chosen]
        truncated_id = inv[last].unit_id
    else:
        pieces = [inv[i].text for i in chosen]
        shortfall = budget_tokens - sum(tokens)

    text = JOIN.join(p for p in pieces if p)
    got = count_tokens(text)
    assert got == budget_tokens - shortfall, (
        f"package is {got} tokens, expected {budget_tokens - shortfall} — the join separator or "
        f"the truncation changed the token count")
    return Package(text=text, tokens=got,
                   unit_ids=[inv[i].unit_id for i in chosen],
                   core_unit_ids=[inv[i].unit_id for i in core_ix],
                   shortfall=shortfall, truncated_unit_id=truncated_id,
                   meta={"doc_id": doc_id, "n_units": len(chosen), "n_core": len(core_ix)})


def gold_token_cost(units: list[Unit], gold: list[GoldSpan]) -> int:
    """Tokens in the contiguous gold-bearing run — what `build_package` compares against B2.

    Descriptive. Lets the frequency of `GoldExceedsBudget` be measured for every arm before any
    generation is paid for, rather than discovered mid-run.
    """
    docs = {g.doc_id for g in gold}
    if len(docs) != 1:
        return -1
    doc_id = docs.pop()
    inv = [u for u in units if u.doc_id == doc_id]
    ix = [i for i, u in enumerate(inv) if _overlaps(u, gold)]
    if not ix:
        return -1
    return sum(count_tokens(inv[i].text) for i in range(min(ix), max(ix) + 1))
