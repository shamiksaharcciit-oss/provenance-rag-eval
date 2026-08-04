# v1.7 Gate 0 — findings before the freeze

**Status:** THE FREEZE HAS NOT HAPPENED. `Plan_v17_ReadingValue_2026-08-01.md` is untracked and
no arm has run. Gate 0's code is built and its tests pass; two findings change text the freeze
would make permanent, so this stops for a ruling rather than committing.
**Date:** 1 August 2026
**Authority for stopping:** the plan's own §0 ("Until that commit exists, nothing here is sealed")
and §5 ("Any wording change after it is a new pre-registration"). v1.6's Gate 0 ran three rounds
before freezing; this is the same discipline.

---

## What is built and green

| | |
|---|---|
| `src/v17/integrity.py` | `integrity_full`, `integrity_single`, `feasible_single`, `score_query` |
| `src/v17/packages.py` | oracle package builder, token-boundary truncation, `gold_token_cost` |
| `src/v17/reading.py` | frozen prompt template, frozen `normalise`, `token_f1`, `exact_containment` |
| `src/v17/e1.py` | `units_at_budget`, `contrast` (R1/R2/R3), `assert_decomposition` |
| `tests/test_v17_integrity.py` + `tests/test_v17_packages.py` | **52 tests, all passing** |
| full suite | **217 passed, 0 failed, exit 0** — nothing outside `v17` touched |

All four required Gate 0 cases are present and named: multi-span gold, a span straddling two units
scoring `integrity_single = 0`, the budget-crossing unit included, and the decomposition summing
exactly on the lattice.

The runner is NOT written. v1.6's precedent is that the run script is authored after the freeze
(`segment_size_sweep.py` docstring, halt condition 10), and the same applies here.

---

## F1 — §2.2 names a provenance rung §2.1's construction cannot produce

§2.2: *"Provenance basis **S2** (own + absorbed) primary, **S1** reported."*
§2.1: reuse the v1.6 arm construction **unchanged**.

Those conflict. The v1.6 builder's `_formatter_rungs` returns `(merge(own + absorbed),
merge(own))` — that is **S2 and S3**. `S1` in the PW-1 ladder is `own + inherited`, and
`inherited` does not exist anywhere in `src/chunkers/` or `src/v16/` (verified by search: zero
occurrences). It is a PW-1 `TightUnit` concept produced by a different rebuild. So `S1` is either
uncomputable here, or — if `inherited` is empty by construction, which it is at this layer —
numerically identical to `S3` while carrying a different name.

**Recommended reading: S3, the conservative floor**, which is what v1.6 actually reported beside
S2. It requires changing one token in §2.2 before the freeze.

This cannot be resolved after freezing: the metric would be computed against a rung the frozen
text does not name.

## F2 — §3.3's "impossible by construction" is false, and I measured how false

§3.1 pads to **exactly** B2 = 1024 tokens, truncating the final unit. §3.3 says a gold span
missing from a package is *"impossible by construction; if observed, apparatus STOP."*

It is not impossible. When the gold-bearing units alone exceed B2, landing on B2 must cut gold.
Measured on the real corpus (no LLM required, no arm value computed — this is the package
builder's precondition checked against the data):

| track | arm | gold-run tokens (median / max) | **over B2** |
|---|---|---|---|
| A | `U256` | 256 / 768 | 0/176 (0.0%) |
| A | **`U768`** | 768 / 1444 | **6/176 (3.4%)** |
| A | `S768` | 761 / 1444 | 4/176 (2.3%) |
| B | `U256` | 512 / 3584 | 25/150 (16.7%) |
| B | **`U768`** | 768 / 3840 | **61/150 (40.7%)** |
| B | `S768` | 764 / 3814 | 57/150 (38.0%) |

`U768` is one half of E2's **primary** contrast. As specified, E2 halts on 6 Track A queries, and
Track B is unrunnable — 41% of its queries would trip the STOP.

`build_package` therefore raises `GoldExceedsBudget` rather than silently deleting the answer and
scoring the arm 0 for a harness decision. **That is a halt, not a fix.** The design choice is
Shamik's, and the options as I see them:

1. **Raise B2** to a value that clears Track A (≥ 1472 clears all six) — but B2 is the
   equal-token matching constant, and a larger package changes what E2 measures.
2. **Declare an exclusion at freeze**: queries whose gold-run exceeds B2 in *either* arm are
   dropped from E2, the count is pre-registered as a limitation, and the excluded set is listed.
   Symmetric across arms, and the exclusion is fixed before any value exists.
3. **Let those packages exceed B2**, keeping gold whole — abandons exact token matching on
   exactly the queries where the arms differ most, which is the worst place to abandon it.
4. **Track A only for E2**, with Track B dropped rather than "descriptive".

I have no recommendation between 1 and 2 that isn't a design preference; both are defensible and
the choice belongs with whoever owns what E2 is measuring. What is not defensible is freezing
§3.3 as written, because it asserts a property the corpus refutes.

## F3 — the prompt template's mid-sentence line break

§3.2 prints the template in a fenced block inside a document wrapped at 96 columns, so its first
sentence carries a newline after *"Quote the answer as exactly as the"*. `PROMPT_TEMPLATE` stores
the instruction **unwrapped** as one logical line, on the reading that no one chooses a newline
mid-sentence. Everything else is character-for-character. This is the only place where "frozen
verbatim" required interpreting the document rather than copying it, so it is flagged rather than
settled silently. If the wrap is wanted, it is a one-line change before the freeze.

## F4 — two corpus facts, both favourable, both measured

- **Multi-document gold: 0/176 and 0/150.** So `integrity_single` is never unsatisfiable for a
  structural reason, and package padding never has to cross a document.
- **Zero-length gold spans: 0/176 and 0/150.** The vacuous-coverage question is moot.

Both are declared in the code and covered by tests anyway, because a metric must be defined on
inputs the corpus does not happen to contain today.

## F5 — one error of mine, reported per A1f

My first probe reported Track B `n = 120`. Wrong: it used `dev_fraction or 0.2`, and Track B's
`dev_fraction` is `0.0`, which `or` overrides. Re-run with the sweep's exact expression gives
**n = 150**, matching v1.6's manifest and the plan. The plan was right and my checker was wrong —
the same class as v1.6's Guard-1 and Guard-4 defects, which is why it is reported rather than
quietly fixed.

---

## What I have not done

- **No freeze commit.** The plan document is untracked. F1 and F2 change its text.
- **No E1 run**, no arm value, no retrieval, no embedding, no LLM call, no spend.
- **No results directory.** The runner creates it with `--out` post-freeze (§A4).
- **No E2 work beyond the builder and its tests**, which is what Gate 0 asks for.
- Nothing outside `v17` modified. Closed artifacts untouched: close-out `235ccfb`, candidates
  `cdd197f`, results `12483f9`, freeze `1b01f9b`.

## What happens on a ruling

F1 and F3 are one-token and one-line edits. F2 needs a design decision. Once all three are
settled I amend the plan, re-run the suite, and make the freeze commit — plan document plus
metric code, prompt template, normalisation code, and tests, in one commit, which is the freeze.
