# v1.8 Gate 0 — build report and findings

**Responds to:** `Plan_v18_InstrumentDivergence_2026-08-01.md` (DRAFT FOR FREEZE, untracked).
**Date:** 1 August 2026
**Executing agent:** the second agent (§8). This session did not run any v1.7 cell.
**Status:** Gate 0 build complete except the determinism probes, which are held for a ruling
(finding **G1**). **Nothing is frozen. Nothing was spent.** Eight findings; three of them
(G1, G3, G4) block the data collection run, and G2 would have silently invalidated it.

---

## 0. Coordination check (§8), performed first

v1.7's B-MiniLM cell **completed** at 14:22 UTC+2 — five arm files plus a manifest under
`results_v17_E1_B_minilm/`, and the runner process is gone. No v17 cell was running at any
point during this build, so §8's condition for heavy local stages was met rather than assumed.

Nothing under `v17/` was written, locked, or read as mutable. All v18 state is under `v18/`.
Free memory recorded as a pair per arm, v1.6 practice: 762 MB at start against the 393 MB known
failure point. The samples are taken **after** each arm, so they bound the margin at six points
rather than continuously; the lowest of the six is 736 MB (Track A `F768`), the highest 1036 MB
(Track B `U768`). No sample approached the failure point. The shared encoder cache was read,
never written.

## 1. What was built

All under `v18/`, per §10. Nothing outside it was edited — including `pyproject.toml`, whose
`testpaths = ["tests"]` therefore still excludes the v18 suite; v18 tests run explicitly with
`python -m pytest v18/tests -q`.

| file | contents |
|---|---|
| `v18/judge_prompts.py` | the six frozen judge prompts, the judge system prompt, call-count constants |
| `v18/instruments.py` | I1's five metric formulas, the parser, the §4 composites, I2 **by import** |
| `v18/contrasts.py` | B1, B2, the B2 identity check, Holm over exactly `F_BIAS` |
| `v18/arms.py` | the three arms via imported `build_arm`, fixed-k retrieval, diagnostics |
| `v18/cost.py` | §6 projection, derived from the prompt constants rather than written down |
| `v18/gate0_build.py` | the runner that produced §2 below |
| `v18/tests/` | 58 tests, all green; full pre-existing suite 224, unchanged and green |

**Identity over assertion, where it binds.** Two of the plan's clauses are made true by
construction rather than by prose:

- §1's "constructed by importing the v1.6 build procedures" — `v18/arms.py` imports `build_arm`
  from `scripts/segment_size_sweep.py`, the same import v1.7's sweep makes.
- §3's "the v1.7 normalisation code by citation" — `v18/instruments.py` imports `token_f1` and
  `normalise` from `src.v17.reading`. `test_i2_token_f1_is_the_v17_object_not_a_copy` asserts
  object identity (`is`), so a transcribed lookalike fails the suite.

**Zero spend is an executed check, not a claim.** `gate0_build.py` asserts
`llm.calls == 0` per arm and per track; `LLMClient.calls` counts only fresh (paid) completions.
The build's own output: **0 fresh LLM calls, 105 cache hits** (F768's formatter calls, all
pre-existing). A second guarantee sits underneath: `ANTHROPIC_API_KEY` is unset in this
environment, so a cache miss raises before a request is constructed — the failure mode is a
stop, not a charge.

## 2. Arms and corpus, measured

Track A n = 176, Track B n = 150, total 326 — §2's `3 × 326 = 978` verified against what the
loaders actually returned, not against the plan's arithmetic.

| track | arm | index units | token mean | **package tokens at k=5** | realised k |
|---|---|---:|---:|---:|---:|
| A | `U256` | 238 | 230.6 | **1260.4** | 5.00 |
| A | `U768` | 90 | 609.8 | **3451.3** | 5.00 |
| A | `F768` | 90 | 583.5 | **3414.9** | 5.00 |
| B | `U256` | 1072 | 249.8 | **1258.7** | 5.00 |
| B | `U768` | 378 | 708.4 | **3715.3** | 5.00 |
| B | `F768` | 381 | 702.7 | **3607.2** | 5.00 |

Two observations, both descriptive and neither a result:

- At fixed k = 5 the `U768` and `F768` packages carry **~2.7× the tokens of `U256`**. That is
  the size confound the design exists to expose, present on purpose (§1), and it is why PD-1 is
  close to guaranteed and why PD-2 is the interesting half of the pair.
- `F768` and `U768` land within ~1–3% of each other on package size. B1's pair is therefore
  near token-matched *by accident of the arms*, not by design — worth one line in the results
  document's limitations, because a reader may assume matching was engineered.

## 3. Findings

### G1 (BLOCKING) — the plan contradicts itself on whether the probe may run before the freeze

- The status header: "until then nothing is sealed and **no judge call, generation call, or arm
  value may be spent**", where "then" is the Gate 0 freeze commit.
- §9: Gate 0 comprises "...determinism probes run on dev only; cost projection per §6. Then
  **STOP for a ruling**." The freeze commit "happens only after that ruling."
- §6: "At Gate 0 the agent reports, before any test-set call: ... **the probe results** ... **No
  test-set spend** before the Gate 0 ruling."

§6 and §9 both require probe results to exist at the Gate 0 report; the header forbids the calls
that would produce them. The two cannot both be honoured: the probe necessarily precedes the
freeze commit. §6 and §9 outnumber the header and §6 bans only *test-set* spend, so the
permissive reading is probably intended — but spending is irreversible and the choice is not
mine to make (v1.7's instruction §1: "If something forces a choice the plan does not determine,
that is itself a STOP — record the state, ask, do not choose").

**I did not run the probes and spent nothing.** Independently, `ANTHROPIC_API_KEY` is unset, so
they could not have run; that is an operational fact, not the reason for the stop.

**Ruling needed:** does Gate 0's probe run on dev before the freeze commit, with the header read
as governing test-set spend only? If yes, G2 must be settled in the same ruling.

### G2 (BLOCKING, and silent) — the determinism probe as specified cannot detect nondeterminism

`LLMClient.complete()` computes a cache key over `(model, system, prompt, temperature,
max_tokens)` and returns the stored text whenever the key file exists
([client.py:100-107](src/llm/client.py#L100-L107)). §2's probe is "20 dev queries × 3 repeats"
— three *identical* prompts. Repeats 2 and 3 are cache hits and return repeat 1's bytes
verbatim.

**The probe would therefore report "byte-identical" for any model, always**, the single-run
branch would be selected unconditionally, and the median protocol §2 declares would never fire.
Nothing downstream would notice: the probe's output is exactly what a genuinely deterministic
model produces.

This is the same species as v1.7 Gate 0's F2 — a procedure that cannot do the job the plan
assigns it — and it is worse in one respect, because F2's design was *unrunnable* whereas this
one runs and returns a confident wrong answer.

**The fix requires a decision, not an implementation.** A cache bypass changes what the probe
measures, so it belongs in the freeze: either (a) the probe writes to a scratch cache directory
discarded per repeat, or (b) `complete()` gains a declared `bypass_cache` path used only by the
probe. (b) touches `src/llm/client.py`, outside v18 paths, which §10 does not authorise — so
(a) is the option available to this agent without a further authorisation. Recommending (a);
not implementing either before the ruling.

A consequence worth stating plainly: **every "determinism verified" claim in this programme that
was checked through this client has the same hole**, if any was. I have not audited v1.6/v1.7
for that and will not — §10 forbids v18 touching their quantities, and the observation is
recorded here for the next pre-registration rather than acted on.

### G3 (BLOCKING) — the median branch exceeds §6's spend gate by ~1.6×

Judge calls per (query, arm) = 12, derived from the prompts: context precision 5 (one per
retrieved unit, K = 5), context recall 1, faithfulness 2 (extraction + verdicts), answer
relevancy 3 (published `strictness`), answer correctness 1.

| stage | calls |
|---|---:|
| generation, test set | 978 |
| judging, test set | 11,736 |
| probe, dev (generation) | 180 |
| probe, dev (judging) | 2,160 |
| **branch: probe byte-identical → single run** | **15,054** ✅ within 25,000 |
| **branch: §2's median fallback (×3 on the test set)** | **40,482** ❌ **exceeds — §6 STOP** |

§6: a projection over 25,000 end-to-end "is a STOP at Gate 0 regardless of other readiness, and
the design gets trimmed by ruling rather than by the agent's discretion." So this is reported,
not solved. The levers, with their costs, so the ruling has them:

| lever | median-branch calls | note |
|---|---:|---|
| as written | 40,482 | |
| `answer_relevancy` strictness 3 → 1 | 34,074 | still over; departs from the published formula |
| median applied to judging only (generation held deterministic) | 38,526 | still over |
| Track A only for the median | ~28,700 | forfeits PD-5, which is Track B's only prediction |
| median ×3 on Track A, single-run on Track B | ~24,400 | within gate; PD-5 becomes single-run |

The last row is the only combination I found that lands inside the gate while keeping all five
predictions scoreable. **I am not taking it** — §6 assigns the trim to the ruling.

Note the interaction with **G2**: if the cache bypass is not fixed, the probe reports
byte-identical, the single-run branch is selected, the projection reads 15,054, and the gate is
never consulted on the branch that actually breaches it.

### G4 (BLOCKING) — the harness's own cost guard aborts the run even in the branch §6 passes

Separate from §6's call gate. `config/default.yaml` sets `cost_guard.max_usd: 60.0`, and
`LLMClient` prices *every* provider at Opus rates ($5 / $25 per MTok,
[client.py:36-37](src/llm/client.py#L36-L37)); `complete()` raises `CostGuardExceeded` once
`est_usd` passes the ceiling.

Estimated from the **measured** package sizes in §2 (assumptions declared in
`v18/cost.py::estimate_usd`: word-count → BPE ×1.3, 100-token answers, 30-token judge replies,
three context passes per query-arm):

| branch | input tok | output tok | USD @ intro $2/$10 | USD @ standard $3/$15 | **USD as the guard computes it ($5/$25)** |
|---|---:|---:|---:|---:|---:|
| single run | 16.7 M | 0.53 M | $38.79 | $58.18 | **$96.97** |
| median ×3 | 45.0 M | 1.43 M | $104.31 | $156.47 | **$260.78** |

**The single-run branch aborts roughly 60% of the way through** on a `max_usd` the run cannot
legally raise: `config/` is outside v18 paths (§10). This needs a ruling whichever way G3 goes.

Pricing note for the ruling: `claude-sonnet-5` is $3.00/$15.00 per MTok, with an introductory
$2.00/$10.00 **through 2026-08-31** — i.e. the run's window if it happens soon. The guard's
Opus-priced arithmetic overestimates true Sonnet cost by ~2.5×, which is conservative in the
right direction but is what will actually fire.

### G5 — `claude-sonnet-5` has no dated snapshot, so §2's pin cannot be satisfied as written

§2 and §3 require the generator and judge "exact version pinned in the manifest". In the current
model catalogue `claude-sonnet-5` is an **alias with no full dated ID** — unlike, say,
`claude-haiku-4-5` (`claude-haiku-4-5-20251001`). There is no string to pin.

The strongest available substitute: record the alias in the manifest *and* record
`response.model` as returned by the API on the first call of each stage, so the served version is
in the record even though it could not be requested. That is a change to what §2 promises and
therefore needs a ruling rather than an agent's substitution. Recommending it.

### G6 — Track B has no dev split, so the probe can only ever run on Track A

`config/tracks/B.yaml` declares `dev_fraction: 0.0`; the build confirms it — Track A dev = 44,
**Track B dev = 0**. §2's "20 dev queries" can only be Track A's. Judge and generator
determinism on Track B's real prose is therefore unprobed, and **PD-5 is a Track B prediction**.

Not blocking — the honest handling is a declared limitation — but it should be declared at the
freeze rather than discovered at Gate 1.

(The falsy-zero trap that produced v1.7's F5 is avoided here: `gate0_build.py` reads
`dev_fraction` through an explicit `is None` sentinel, which is v1.7 Gate 0's §5 suggestion
adopted rather than merely noted.)

### G7 — PD-2 predicts a *majority*; `F_BIAS` member B2 tests a *difference*

PD-2: "the **majority** of that judge-visible gain is reproduced by `U768`". B2 is defined (§4)
as `(F768 − U256) − (F768 − U768)` on the context composite, tested by bootstrap + permutation
against zero. That test answers "is the size-attributable component non-zero", not "is it more
than half".

Note also that B2 **telescopes exactly**: the `F768` terms cancel, leaving `U768 − U256`. The
plan's un-cancelled form says what it means, so `b2_per_query` computes it as written and
`assert_b2_identity` pins the cancelled form against it on the same vectors — the reading and
the arithmetic check each other rather than one being trusted.

But the identity also makes the gap concrete: B2 contains no `F768` information at all, so no
test on B2 can express a claim about what fraction of `F768`'s gain is size. A ratio
(`(U768−U256) / (F768−U256)`) would, but ratios of small noisy denominators are unstable and no
such quantity is declared.

**Ruling needed:** how is PD-2 scored? Options: (a) score PD-2 as "B2 > 0 with `p_holm` < 0.05",
accepting that "majority" is loosened to "present"; (b) declare the ratio now as a *descriptive*
companion with PD-2 scored against it by direction only, no test; (c) reword PD-2 before the
freeze. All three are legitimate; (c) is cleanest and is available because nothing is sealed.

### G8 — RAGAS is not installed; §3's second branch is selected, with a reason

`import ragas` → `ModuleNotFoundError`. §3's rule then selects "implement the published formulas
directly," which `v18/judge_prompts.py` and `v18/instruments.py` do.

Recording *why* installation was not attempted, since the rule invites it: `ragas` pulls a
langchain adapter stack into an environment whose pins (torch 2.13.0, transformers 5.14.1,
numpy 2.2.6) are the ones under which v1.6's and v1.7's `recall@budget` reproduction checks
pass. Perturbing that environment to obtain a metric library would put the apparatus those
checks defend at risk for no measurement gain. §3's own sentence governs either way — "the
metric code frozen at Gate 0 is canonical over any library documentation."

Consequence to declare at the freeze: v1.8's I1 is a **reimplementation of RAGAS-class
formulas**, not RAGAS. That is a limitation for the results document, and it slightly weakens the
"evaluated exactly as the field would evaluate it" framing in §0.

## 4. Two judgements made, both minor and both visible

Neither is a finding; both are recorded so they are legible rather than discoverable.

- **`faithfulness` of a claimless answer returns 1.0, not NaN.** RAGAS returns NaN. A NaN
  propagating into a paired contrast silently drops that query from one arm and breaks the
  pairing every statistic here depends on. The count of empty-statement answers is reported per
  arm so the substitution is visible. If the ruling prefers NaN-with-listwise-deletion, say so.
- **Composites are unweighted means**, direction declared in code and pinned by tests. Any
  weighting would be a free parameter with no principled setting, and an unprincipled one chosen
  at Gate 0 is still chosen by the agent.

**Considered and dismissed:** generator and judge are the same model (`claude-sonnet-5`), so I1
scores the judge's own outputs. Self-preference is real, but it applies **equally to both arms**
— the same generator produced both answers — so it does not bias B1's *contrast*, which is a
within-query difference. Worth one line in limitations; not a threat to the design.

## 5. What was NOT done, and why

- No determinism probe, no generation call, no judge call, no arm *value* (G1). 0 fresh calls.
- No freeze commit. §9 puts it after the ruling; this document precedes it.
- No `config/` edit to raise `max_usd`, no `src/llm/client.py` edit for the cache bypass — both
  outside v18 paths (§10), both needing a ruling.
- No I1 or I2 value computed on any test query. The build produced inventories and ranked
  contexts — the input generation would consume — and stopped there.
- No packaging, sequencing, or release consideration of any kind (§7, §10).

## 6. Item-7 self-check

Every count and universal in this document names its procedure, and each was executed against
the final text:

| claim | procedure | output |
|---|---|---|
| 224 pre-existing tests green | `python -m pytest -q` | 224 passed |
| 58 v18 tests green | `python -m pytest v18/tests -q` | 58 passed |
| 0 fresh LLM calls | `assert llm.calls == 0` per arm and track, in `gate0_build.py` | held; 105 cache hits |
| n = 176 / 150 / 326 | `load_track_dataset` + `split_dev_test` in the build | as tabled |
| package tokens, unit counts | `v18/arms.py::retrieve_fixed_k` + `inventory_diagnostics` | as tabled |
| 12 judge calls per (query, arm) | `sum(CALLS_PER_QUERY_ARM.values())`, pinned by a test | 12 |
| 15,054 / 40,482 | `v18/cost.py::project` on measured n | as tabled |
| USD estimates | `v18/cost.py::estimate_usd` on measured package sizes | as tabled |
| Track B dev = 0 | build log, explicit `is None` sentinel | `dev=0 dev_fraction=0.0` |
| `ragas` absent | `import ragas` | `ModuleNotFoundError` |
| no v17 cell running | process check + `results_v17_E1_B_minilm/` complete at 14:22 | confirmed |

Artifacts: `v18/results_gate0/gate0_manifest.json` and six `contexts_{track}_{arm}.json`.

## 7. Requested rulings, in the order they block

1. **G1** — may the dev determinism probe run before the freeze commit? (And note
   `ANTHROPIC_API_KEY` is unset; the run needs a credential either way.)
2. **G2** — which cache-bypass, and is the `src/llm/client.py` option authorised? Without this,
   the probe is decorative and G3's gate is never consulted on the branch that breaches it.
3. **G3** — which trim, given the median branch is 1.6× over §6's gate.
4. **G4** — `max_usd`: raise it (a `config/` edit this plan does not authorise), or accept a
   run that aborts partway.
5. **G5** — pin the alias plus recorded `response.model`, or something stronger.
6. **G7** — how PD-2 is scored; cleanest before the freeze, since nothing is sealed.
7. **G6, G8** — no decision needed; confirm they are declared at the freeze as limitations.

Then, on those rulings: amend the plan, freeze (plan + code + prompts + tests, one commit), run
the probes, report the projection against §6 again, and stop for the spend gate.

Confirmed on this side: nothing spent, no arm value exists, no v18 commit made, nothing under
`v17/` touched, working tree carries only new `v18/` paths and this document.
