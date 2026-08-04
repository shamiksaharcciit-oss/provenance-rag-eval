"""§9 — judge-prompt snapshot tests, and the citation checks.

The snapshot is a digest per prompt. Its job is not to prove the prompts are *good*; it is to
make any later edit to them loud. "The exact prompts the judge receives are part of the freeze"
(§3) is only enforceable if changing one breaks something, and prose in a plan cannot break.

The citation tests are the same idea applied to §2 and §3's two "by citation" clauses: they
assert that v18 is using the v1.7 objects themselves rather than lookalikes. Identity over
assertion — the freeze report's first promoted practice, applied where it actually binds.
"""
from __future__ import annotations

import hashlib

import pytest

from v18 import instruments
from v18.judge_prompts import (ALL_PROMPTS, ANSWER_RELEVANCY_STRICTNESS,
                               CALLS_PER_QUERY_ARM, FIXED_K, JUDGE_SYSTEM, render)

#: Digests of the prompts as frozen at Gate 0 build time. Any edit to a prompt fails here.
PROMPT_SHA256 = {
    "answer_correctness": "58e7a10a4ed9e6ba73b8a51483eed14743f6057791a6a3ee85fc39c427fda366",
    "answer_relevancy": "1046a338166b1ca4071f649732a8555d1bd3c9df5449277a71e0eccc73548b45",
    "context_precision": "29558429941039ea7a5da0608ba05f7d56f3acc97791bead0b311f330c55acb3",
    "context_recall": "5989f47c025a99c4cb35c9b4da8a5c0715b272d5cce34d4121f286b803658a45",
    "faithfulness_statements": "76b6e32fe4283b35bbac2b6ed950c94d78d09c8c3df67bbf8996be8ec3d400c3",
    "faithfulness_verdicts": "4452cd52411ea8ef1147c694c5dfb0590f823911f018b78cff66d0b5ec8f7837",
}
JUDGE_SYSTEM_SHA256 = "47ea584462c2055034637be941cc57de9338241e126c2b1014a9ee70e551f33e"


def test_prompt_snapshots_are_unchanged():
    assert set(ALL_PROMPTS) == set(PROMPT_SHA256), (
        "a prompt was added or removed; the snapshot set must be updated deliberately")
    for name, text in sorted(ALL_PROMPTS.items()):
        got = hashlib.sha256(text.encode()).hexdigest()
        assert got == PROMPT_SHA256[name], f"prompt {name!r} changed: {got}"


def test_judge_system_prompt_snapshot():
    assert hashlib.sha256(JUDGE_SYSTEM.encode()).hexdigest() == JUDGE_SYSTEM_SHA256


def test_every_prompt_declares_its_json_reply():
    """A prompt that never says what to reply makes the parser the metric."""
    for name, text in ALL_PROMPTS.items():
        assert "Reply exactly:" in text, f"{name} does not state its reply format"


def test_render_is_literal_and_survives_braces():
    """Package and answer text contain braces; `str.format` would raise or interpolate."""
    out = render("Q: {question} / C: {context}", question="what is {x}?", context="a {b} c")
    assert out == "Q: what is {x}? / C: a {b} c"


def test_render_leaves_unknown_placeholders_alone():
    assert render("{a}{b}", a="1") == "1{b}"


# ------------------------------------------------------------------ §2/§3 "by citation" checks

def test_i2_token_f1_is_the_v17_object_not_a_copy():
    """§3: I2 uses the v1.7 normalisation code *by citation*, canonical at e19dd35."""
    from src.v17 import reading
    assert instruments.token_f1 is reading.token_f1
    assert instruments.normalise is reading.normalise


def test_v17_prompt_is_reusable_verbatim_by_import():
    """§2: v1.8 generation reuses the v1.7 E2 frozen prompt verbatim, by citation.

    The generation runner does not exist yet (no spend before the ruling), so what is pinned
    here is that the object is importable and unmodified — the same check the runner will make.
    """
    from src.v17.reading import PROMPT_TEMPLATE, render_prompt
    assert "{package}" in PROMPT_TEMPLATE and "{query}" in PROMPT_TEMPLATE
    assert PROMPT_TEMPLATE.startswith("Answer the question using only the provided context.")
    assert "NOT FOUND" in PROMPT_TEMPLATE
    # one logical line for the instruction (v1.7 PF-3), i.e. no newline before "If the context"
    head = PROMPT_TEMPLATE.split("\n")[0]
    assert head.endswith("reply exactly: NOT FOUND.")
    assert render_prompt("ctx", "q").count("ctx") == 1


# ----------------------------------------------------------------------------- call accounting

def test_calls_per_query_arm_matches_the_prompt_inventory():
    """The projection counts what the prompts actually issue (§6)."""
    assert CALLS_PER_QUERY_ARM["context_precision"] == FIXED_K
    assert CALLS_PER_QUERY_ARM["faithfulness"] == 2, "extraction + verdicts"
    assert CALLS_PER_QUERY_ARM["answer_relevancy"] == ANSWER_RELEVANCY_STRICTNESS
    assert sum(CALLS_PER_QUERY_ARM.values()) == 12


@pytest.mark.parametrize("name", sorted(ALL_PROMPTS))
def test_prompts_carry_no_trailing_whitespace_lines(name):
    """Whitespace drift is how two 'identical' prompts stop hashing alike."""
    for line in ALL_PROMPTS[name].split("\n"):
        assert line == line.rstrip(), f"{name}: trailing whitespace in {line!r}"
