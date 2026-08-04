"""Negative control for template §A2 (handoff 2026-07-29 §7b).

§A2 says a cheap downstream step must never destroy an expensive completed result. v1.5's
`run_v15.py` violated it — results were written only at the end, so a segfault during Track B
destroyed six completed Track A conditions. The fix was per-condition persistence.

§A1b says a guard that has never been *observed* failing is a regression guard, not evidence.
That is the gap these tests close. The control is the one the incident implies: **kill the
process mid-run and assert completed conditions survive on disk** — with an uncatchable kill
from the parent (`TerminateProcess` on Windows, `SIGKILL` elsewhere), not an exception the
child could have handled.

The deliberate violation is the write-at-end shape itself, run through the same kill, and it
must lose everything. Without that arm, a passing test proves only that files can be written.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPLETED, KILLED_DURING = 2, 3   # conditions 1..2 finish; the process dies inside condition 3

# Shared child-process preamble: build fake condition rows and signal readiness by file.
_PREAMBLE = """
import json, sys, time
from pathlib import Path
sys.path.insert(0, r"{root}")
from src.run_v15 import _persist

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
sentinel = Path(sys.argv[2])
cfg = {{"embedding": {{"model": "m", "revision": "r"}}, "seed": 1,
       "index": {{"candidate_pool": 50, "k_rrf": 60}}}}

def row(i):
    return {{"condition": f"C{{i}}", "child_tokens": 128, "n_queries": 3, "track": "A",
            "baseline": {{"5": 0.5}}, "s2b": {{"5": 0.6}}, "diagnostics": {{}},
            "_vectors": {{"base": [1, 0, 1], "s2b": [1, 1, 1]}}}}
"""

CHILD_PER_CONDITION = _PREAMBLE + """
rows, pq = [], []
for i in range({completed}):
    rows.append(row(i)); pq.append({{"condition": f"C{{i}}"}})
    _persist(out, "run-x", cfg, rows, pq)          # THE GUARD: write after every condition
rows.append(row({killed}))                          # condition {killed} starts...
sentinel.write_text("ready")
time.sleep(120)                                     # ...and the parent kills us inside it
"""

CHILD_WRITE_AT_END = _PREAMBLE + """
rows, pq = [], []
for i in range({completed}):
    rows.append(row(i)); pq.append({{"condition": f"C{{i}}"}})
                                                    # THE VIOLATION: nothing written yet
rows.append(row({killed}))
sentinel.write_text("ready")
time.sleep(120)
_persist(out, "run-x", cfg, rows, pq)               # unreachable — this is the v1.5 defect
"""


def _run_until_ready_then_kill(tmp_path: Path, source: str) -> Path:
    """Start the child, wait for it to reach the kill point, then terminate it uncatchably."""
    out = tmp_path / "results"
    sentinel = tmp_path / "ready"
    script = tmp_path / "child.py"
    script.write_text(textwrap.dedent(source).format(
        root=str(ROOT), completed=COMPLETED, killed=KILLED_DURING), encoding="utf-8")

    proc = subprocess.Popen([sys.executable, str(script), str(out), str(sentinel)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.time() + 60
        while not sentinel.exists():
            if proc.poll() is not None:
                pytest.fail(f"child exited early: {proc.communicate()[1].decode()[:800]}")
            if time.time() > deadline:
                pytest.fail("child never reached the kill point")
            time.sleep(0.05)
        proc.kill()          # TerminateProcess / SIGKILL — not catchable, like a segfault
    finally:
        proc.wait(timeout=30)
    assert proc.returncode != 0, "the child must have died, not exited cleanly"
    return out


def test_completed_conditions_survive_a_kill_mid_run(tmp_path):
    """The guard, demonstrated under the failure it exists for."""
    out = _run_until_ready_then_kill(tmp_path, CHILD_PER_CONDITION)

    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    survived = [r["condition"] for r in results["results"]]
    assert survived == [f"C{i}" for i in range(COMPLETED)], survived
    assert f"C{KILLED_DURING}" not in survived, "a condition that never finished must not appear"

    # The statistics must be recomputable from what survived — losing the vectors would make
    # the surviving rows unusable, which is the same loss one indirection later.
    vecs = json.loads((out / "vectors.json").read_text(encoding="utf-8"))
    assert len(vecs) == COMPLETED and all(v["base"] and v["s2b"] for v in vecs)

    lines = (out / "per_query.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == COMPLETED and all(json.loads(ln) for ln in lines)


def test_the_write_at_end_shape_loses_everything_under_the_same_kill(tmp_path):
    """The deliberate violation — §A1b. This is the v1.5 incident reproduced.

    If this test ever passes by finding files on disk, the control above has stopped
    discriminating and proves nothing.
    """
    out = _run_until_ready_then_kill(tmp_path, CHILD_WRITE_AT_END)
    assert not (out / "results.json").exists(), \
        "write-at-end must lose the completed conditions — otherwise the control is inert"
    assert not (out / "vectors.json").exists()
    assert not (out / "per_query.jsonl").exists()
