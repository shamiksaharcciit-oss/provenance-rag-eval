"""§10/PF-4 — the one authorised edit outside `v18/`, kept honest.

The ruling authorises exactly one line of `config/default.yaml` to move: `cost_guard.max_usd`,
raised to 150.0 in the freeze commit and reverted to 60.0 in the results commit. "Exactly one
line" is the kind of promise that decays quietly — an unrelated tweak riding along in the same
file would never be noticed by any other check in this repo.

So the scope is enforced rather than asserted: this test diffs the working file against `HEAD`
and fails if anything other than the `max_usd` line differs. It is the same move as importing
`build_arm` instead of copying it — make the constraint true by construction, not by discipline.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "default.yaml"

#: The two states §10 authorises. Any third value is an unauthorised edit.
AUTHORISED_MAX_USD = {60.0, 150.0}


def _head_text(rel: str) -> str | None:
    # `encoding="utf-8"` is load-bearing: the default on Windows is cp1252, which mangles the
    # `§` characters in this repo's configs and makes every such line look edited.
    try:
        out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True,
                             text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - environment dependent
        return None
    return out.stdout if out.returncode == 0 else None


def test_max_usd_is_one_of_the_two_authorised_values():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert cfg["cost_guard"]["max_usd"] in AUTHORISED_MAX_USD, (
        f"cost_guard.max_usd is {cfg['cost_guard']['max_usd']}; §10 authorises only "
        f"{sorted(AUTHORISED_MAX_USD)} (60.0 outside the run, 150.0 during it)")


def test_the_rest_of_the_cost_guard_block_is_untouched():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert cfg["cost_guard"]["max_llm_calls"] == 100_000
    assert set(cfg["cost_guard"]) == {"max_llm_calls", "max_usd"}


def test_no_line_of_the_config_other_than_max_usd_differs_from_head():
    """§10: 'No other line of that file'. Enforced against `HEAD`, not trusted."""
    head = _head_text("config/default.yaml")
    if head is None:
        pytest.skip("config/default.yaml not in HEAD (or git unavailable)")
    head_lines = head.splitlines()
    work_lines = CONFIG.read_text(encoding="utf-8").splitlines()
    assert len(head_lines) == len(work_lines), (
        "config/default.yaml changed line count; §10 authorises a single value edit")
    differing = [(i, a, b) for i, (a, b) in enumerate(zip(head_lines, work_lines), 1) if a != b]
    for lineno, before, after in differing:
        assert "max_usd" in before and "max_usd" in after, (
            f"unauthorised edit at config/default.yaml:{lineno}: {before!r} -> {after!r}")
    assert len(differing) <= 1, f"more than one line differs: {differing}"


def test_the_pricing_inaccuracy_is_documented_not_repaired():
    """PF-4/G4: the guard prices every provider at Opus rates. That stays, by ruling."""
    client_src = (ROOT / "src" / "llm" / "client.py").read_text(encoding="utf-8")
    assert "_USD_PER_INPUT_TOKEN = 5.0 / 1_000_000" in client_src, (
        "the guard's Opus-rate pricing was changed; §10 authorises no edit to src/llm/client.py "
        "and PF-4 documents this inaccuracy rather than fixing it")
