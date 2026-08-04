"""v1.8 PF-13 — the frozen codebooks that make every `custom_id` field a closed vocabulary.

G12: the API accepts `^[a-zA-Z0-9_-]{1,64}$` and every query id in both tracks violates it
(`A-040-marlin-planner::syn`, `1911.07555::q5`), as did PF-12's `:` separator. The repair ruled
in `Decisions_v18_G12_2026-08-01.md` removes free text from the identity: each field is drawn
from a closed, hyphen-free set, so the uniform hyphen split is unambiguous **by construction**
rather than recovered by a special-cased parser.

`custom_id` and this codebook **jointly** constitute the identity — that is the exact and only
amendment to PF-12 §2's "sole record", and the codebook is committed with its SHA-256 in the
manifest so the pointer cannot drift from what it points at.

One extension the ruling's format implies but does not spell out: the generation stage has no
metric, and `{metric}` sits in a fixed position. Leaving it empty would make the field count
vary and reintroduce exactly the parsing conditionality the ruling removed, so generation uses
the closed code **`na`**. It is declared here rather than assumed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEBOOK_DIR = ROOT / "v18" / "codebooks"

#: Two-letter codes for the five I1 metrics, plus `na` for the metric-free generation stage.
METRIC_CODES = {
    "context_precision": "cp",
    "context_recall": "cr",
    "faithfulness": "fa",
    "answer_relevancy": "ar",
    "answer_correctness": "ac",
    None: "na",
}
CODE_TO_METRIC = {v: k for k, v in METRIC_CODES.items()}

#: Closed sets for every remaining field. PF-15 splits judging into j1/j2 because
#: faithfulness is extract-then-verify and stage 2's prompt depends on stage 1's reply.
STAGE_CODES = {"generate": "g", "judge1": "j1", "judge2": "j2"}
CODE_TO_STAGE = {v: k for k, v in STAGE_CODES.items()}

#: PF-15 — the call plan, DERIVED from the frozen per-metric counts rather than restated.
#: `(stage, metric) -> number of sub-calls`, and whether the metric concerns a generated answer.
#: G14 happened because an identity was specified over "one call per metric" while the real
#: plan sat frozen in `CALLS_PER_QUERY_ARM` since Gate 0. Deriving it here means the census and
#: the request builder cannot disagree: one is a function of the other.
ANSWER_LEVEL_METRICS = ("faithfulness", "answer_relevancy", "answer_correctness")
CONTEXT_LEVEL_METRICS = ("context_precision", "context_recall")


def call_plan() -> list[tuple[str, str, int, bool]]:
    """`(stage, metric, n_sub, concerns_answer)` for every metric, derived from the frozen counts.

    `faithfulness`'s two calls are one extraction (j1) and one verdict pass (j2); every other
    metric issues all its calls in j1.
    """
    from v18.judge_prompts import CALLS_PER_QUERY_ARM
    plan = []
    for metric, n in CALLS_PER_QUERY_ARM.items():
        concerns_answer = metric in ANSWER_LEVEL_METRICS
        if metric == "faithfulness":
            assert n == 2, f"faithfulness is extract-then-verify; got {n} calls"
            plan.append(("judge1", metric, 1, concerns_answer))
            plan.append(("judge2", metric, 1, concerns_answer))
        else:
            plan.append(("judge1", metric, n, concerns_answer))
    return plan

ARM_CODES = {"U256": "u256", "U768": "u768", "F768": "f768"}
CODE_TO_ARM = {v: k for k, v in ARM_CODES.items()}

TRACKS = ("A", "B")

#: Zero-padding width for the query index. Both tracks are < 1000 queries.
INDEX_WIDTH = 3


def codebook_path(track: str) -> Path:
    return CODEBOOK_DIR / f"query_index_{track}.json"


def write_codebook(track: str, query_ids: list[str]) -> dict:
    """Freeze a track's ordered query list. Position IS the index; order is the frozen split's."""
    assert len(set(query_ids)) == len(query_ids), f"track {track}: duplicate query ids"
    assert len(query_ids) < 10 ** INDEX_WIDTH, (
        f"track {track}: {len(query_ids)} queries needs more than {INDEX_WIDTH} index digits")
    CODEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"track": track, "n": len(query_ids), "index_width": INDEX_WIDTH,
               "ids": list(query_ids),
               "_note": ("position in `ids` is the index used by custom_id; this file and the "
                         "custom_id jointly constitute the identity (PF-13)")}
    codebook_path(track).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_codebook(track: str) -> dict:
    return json.loads(codebook_path(track).read_text(encoding="utf-8"))


def codebook_sha256(track: str) -> str:
    return hashlib.sha256(codebook_path(track).read_bytes()).hexdigest()


class _Index:
    """Cached id -> index lookups, so encoding 17k requests does not rescan a list each time."""

    def __init__(self):
        self._fwd: dict[str, dict[str, int]] = {}
        self._rev: dict[str, list[str]] = {}

    def _ensure(self, track: str) -> None:
        if track not in self._fwd:
            ids = load_codebook(track)["ids"]
            self._rev[track] = ids
            self._fwd[track] = {qid: i for i, qid in enumerate(ids)}

    def index_of(self, track: str, query_id: str) -> int:
        self._ensure(track)
        try:
            return self._fwd[track][query_id]
        except KeyError:
            raise KeyError(
                f"query id {query_id!r} is not in track {track}'s frozen codebook; the codebook "
                f"and the run's query list have diverged (PF-13)") from None

    def id_of(self, track: str, index: int) -> str:
        self._ensure(track)
        return self._rev[track][index]

    def size(self, track: str) -> int:
        self._ensure(track)
        return len(self._rev[track])


INDEX = _Index()


def assert_bijections() -> None:
    """Every code table must be a bijection, or an id cannot be decoded back to its meaning."""
    for name, table in (("metric", METRIC_CODES), ("stage", STAGE_CODES), ("arm", ARM_CODES)):
        assert len(set(table.values())) == len(table), f"{name} codes are not unique: {table}"
        for key, code in table.items():
            assert "-" not in code, f"{name} code {code!r} contains the separator"
            assert code.isalnum(), f"{name} code {code!r} is not alphanumeric"
