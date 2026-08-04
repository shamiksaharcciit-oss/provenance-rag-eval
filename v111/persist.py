"""v1.11 — the persist-every-output acceptor (plan §7, PF-G1).

v1.9 kept each arm's median F1 and rep 0's text, discarding the other two repetitions. That
silently foreclosed a declared downstream stage and cost 1,056 regeneration calls; it then
inconvenienced v1.11's E-B, which could not reuse packages that were never written. The standing
order is now CHECKED rather than intended: every repetition's output, and every package text.
"""
from __future__ import annotations


class PersistenceIncomplete(AssertionError):
    """A record kept a summary where the standing order requires every output."""


def assert_every_output_persisted(record: dict, reps: int) -> None:
    """`record` maps query_id -> arm -> {"answers": [...], "packages": str}."""
    for qid, arms in record.items():
        for arm, d in arms.items():
            ans = d.get("answers")
            if not isinstance(ans, list) or len(ans) != reps:
                raise PersistenceIncomplete(
                    f"{qid}/{arm}: {0 if ans is None else len(ans)} answers for {reps} reps — "
                    f"every repetition's output must be persisted, not only its summary")
            if not d.get("packages"):
                raise PersistenceIncomplete(f"{qid}/{arm}: package text not persisted")
