# Experiment plan — v1.6, the segment-size / retrieval-budget confound

**Date:** 31 July 2026 · **Supersedes:** `Handover_v16_SegmentSize.md` wherever they differ ·
**Gate 0:** `v16_Gate0_Findings_2026-07-31.md`, three rounds, commits `86dfa07`, `4851f58`,
`d43063f` · **Status at writing: no pre-registration stamped, no script, no arm value.**

v1.6 **stands beside** v1.1. It amends nothing, supersedes no published number, and does not
reopen PW-1, whose conclusion is closed and stays as written.

---

## 0. The question, and what is actually new here

Every published comparison in this programme measures a formatted corpus against an original
corpus, and in every one, two things move at once: **the words change** and **the cuts move**.
This experiment separates them by scoring the **original, unedited corpus** under the formatter's
segmentation geometry, and asking how much of the advantage survives when no word changes.

**What is new, stated plainly because Gate 0's G10 changed the answer.** Under `recall@5` at
m = 768, this design is a **reproduction check** — the answer is already published:

| Arm | Published as | recall@5 |
|---|---|---|
| `U768` | C0 | 0.7841 |
| `S768` | C3-markeronly | 0.7955 |
| `F768` | C3 | 0.8182 |

Seam ≈ **+0.011**, edit ≈ **+0.023**. The genuinely new information is in exactly three places:
the **`recall@budget(1920)`** metric, the **sizes other than 768**, and the **`F@S` arm**. That a
known row reproduces is a reason to trust the unknown rows — but only because it is declared here
rather than discovered by a reader.

**Reproduction is void across embedders.** Those are `all-MiniLM-L6-v2` numbers. The primary cell
runs MiniLM, so the reproduction check is live there. No reproduction claim may be made from the
bge cell; absolute levels are not comparable across embedders (Template §B).

---

## 1. Gate 0 findings, carried

Established from source and artifact before any design was settled. File and line in
`v16_Gate0_Findings_2026-07-31.md`.

| # | Finding |
|---|---|
| G1 | C3's published corpus used `soft_target_tokens` **768** (`run.py:46-48`; `chosen_chunk_sizes`), overriding the 384 in `C3.yaml` |
| **G2** | **RECOVERED, VERIFIED.** Published C0 used `overlap_frac = 0.0` and therefore *is* `U768`. Two exact integer signals: corpus 54,886 tokens vs U768@0.0's 54,886 (residual **+0**), and unit count **90** vs 91 at overlap 0.1 and 95 at 0.2. Assumptions: one tokenizer both sides; the naive chunker adds and drops no text; no other stage could restore both signals coincidentally |
| G3 | `_common_size_control` (`run.py:312-333`) **hardcodes** `soft_target_tokens: 384` then re-chunks at 256 — a different formatted corpus from published C3's |
| G4 | C3-* ablations inherit C3's swept 768 (`run.py:230-232`). C3-nosize's 1552 units come from `right_size: False`, not a size difference |
| G5 | The eight 90-unit values are genuine per-condition measurements — eight identical counts carry **eight different token means** |
| **G6** | The original byte-verbatim gate **failed 10/10 on whitespace alone**. `_emit` joins sentences with a single space (`formatter.py:302`) and `sentence_spans` excludes inter-sentence whitespace. **No word, identifier or number changes.** Gate weakened to three parts; see §6 |
| **G7** | The LLM path is gated on `markers_only`, **not** on `reference_resolution`/`dedup` (`formatter.py:184`), and `_chunk_llm` calls `complete()` unconditionally. With both ops off the system prompt's ops list is empty, so the cache key differs: **FULL 45/45 cached, SEAM 0/45**. SEAM as first specified would have made 45 fresh LLM calls on a track declaring `requires_llm: false` |
| **G7b** | **`markers_only: True` overrides `right_size`** (`formatter.py:243`): right-sizing runs regardless. This is why `C3-markeronly` lands on 90 units and not `C3-nosize`'s 1552 — **a reader of `C3-markeronly.yaml` alone would predict the wrong unit count.** Recorded as a finding, not fixed: this experiment measures the published formatter, not a repaired one |
| G8 | Formatter units carry own + absorbed only (`formatter.py:306-313`); measured width 0.9860 SEAM / 1.0177 FULL. The inheritance path (`formatted.py:86-94`) is **not exercised by any v1.6 arm** |
| **G9** | **FALSIFIED.** `_right_size` is pure arithmetic applied after `complete()`, so the LLM does not choose boundaries — but it groups by `count_tokens(st.text)` over `st.kept`, and the LLM sets **both**. **0/45 Track A documents share boundaries** between SEAM(768) and FULL(768); `A-000` moves its interior boundary 283 characters |
| G10 | **SEAM *is* `C3-markeronly`** — same parameter set, `run.py:230-232` supplying 768. Rebuilt: 90 units, token_mean 609.84, identical to published |

**Neither `_emit` nor line 243 is fixed.** Repairing the object under measurement would mean
`F768` no longer reproduces the published C3 corpus, and that reproduction is one of the few
things tying this experiment to the published record.

---

## 2. Arms

Defined **inline in the script**, never in `config/conditions/` — `all_condition_ids()` globs that
directory and a new YAML there would silently join every future full run. `overlap_frac` is pinned
at `0.0` in every arm so overlap is not a second free variable.

**UNCUT** — unedited text, dumb cutter, size swept:
```python
U = {"id": f"U{n}", "chunker": "naive", "params": {"chunk_tokens": n, "overlap_frac": 0.0}}
```
for n in `[128, 256, 384, 512, 768]` — the existing `sweep.baseline_chunk_tokens` grid, unchanged.

**UNCUT-ws** — the whitespace control (see §3). UNCUT's units with
`re.sub(r"\s+", " ", text)` applied to **unit text only**; `source_ranges` untouched.

**SEAM** — unedited vocabulary, formatter's segmenter only, **deterministic path**:
```python
S = {"id": f"S{n}", "chunker": "formatter",
     "params": {"soft_target_tokens": n, "reference_resolution": False, "dedup": False,
                "right_size": False, "boundary_markers": False, "markers_only": True,
                "verbatim_guardrail": True, "diff_gate": True}}
```
for n in `[384, 768]`. **`markers_only: True` is correctness, not economy** (G7): it keeps a
generative model with an empty instruction list out of the path of the one arm whose entire
evidential value rests on its text being unchanged. Any perturbation it introduced would break G6
non-deterministically, run to run. That it also avoids 45 fresh calls is secondary.

**FULL** — the complete formatter pass:
```python
F = {"id": f"F{n}", "chunker": "formatter",
     "params": {"soft_target_tokens": n, "reference_resolution": True, "dedup": True,
                "right_size": True, "boundary_markers": True, "verbatim_guardrail": True,
                "diff_gate": True}}
```
for n in `[384, 768]`. Fully cache-served: prompts do not depend on `soft_target_tokens`, so
F384 and F768 share C3's entries, 45/45.

**`F@S`** — FULL's edited sentences, SEAM's boundaries. `src/v16/regroup.py`.

> **The assignment rule IS the arm definition.** Each of FULL's kept sentences goes to the SEAM
> segment containing the start of its first source range; sentences are concatenated in order
> within each segment through **FULL's own `_emit`**, so a unit's `source_ranges` are the union of
> its sentences' ranges by the same rule FULL applies. A different rule is a different experiment.

`F@S` rather than `S@F`, on the record as a decision: it is the conservative direction (it denies
edited text its preferred seams, so a positive result survives its own worst case); it puts no
treatment-derived information inside a control; and it is the direct-effect estimand §0 asks for.

**`S@F`** — optional, **declared secondary**, interaction-only. Its sole reported use is the
**magnitude of the interaction** between text and boundary placement. It is never an alternative
estimate of the editing effect, enters no decision rule, and is in no Holm family.

---

## 3. The decomposition

```
D_size(m)   = U(m)    − U256        cutting geometry alone, no editing
D_ws(m)     = U(m)-ws − U(m)        the _emit whitespace artifact (UPPER BOUND)
D_seam(m)   = S(m)    − U(m)-ws     seam placement, whitespace-matched, no editing
D_edit(m)   = F(m)    − S(m)        TOTAL effect of enabling editing, boundary shift included
D_total(m)  = F(m)    − U256

splitting the treatment term:
D_text(m)   = F@S(m)  − S(m)        editing at SEAM's seams           (direct)
D_reseam(m) = F(m)    − F@S(m)      the boundary shift editing causes (indirect)
D_edit(m)   = D_text(m) + D_reseam(m)
```

**`D_edit` is the treatment and is relabelled**, per the G9 ruling: *the total effect of enabling
the editing pass, including the boundary shift the editing induces.* The shift is a **downstream
consequence of the treatment**, not an outside variable contaminating it — so `D_edit` is the
total effect as deployed, which is the quantity a reader deciding whether to switch the formatter
on actually needs. G9 falsified the *description*, not the measurement.

**`D_size` and `D_seam` are untouched by G9.** Both run on unedited text over an identical
sentence list. The damage was contained to one term.

**`D_ws` is an upper bound, not an exact replication:** collapsing `\s+` across a whole unit also
collapses intra-sentence runs, which `_emit` preserves. Reported whichever way it falls; if it is
at or near zero the artifact is verified harmless and `D_seam` needs no correction.

**A null `D_edit` is not decomposed.** If `D_edit` is indistinguishable from zero the branch is
KILL, and splitting a null into two components is arithmetic on noise, not a finding. Frozen now,
before the value exists, because afterwards it will be tempting.

Both identities telescope by construction and are asserted to exact equality on point estimates —
as **wiring checks, not validity checks**. They catch a transposed variable. They are not evidence
that the decomposition means anything.

**`F@S` differs from `F` on 45/45 Track A documents** (measured, `d43063f`). So `D_reseam` is not
zero by construction anywhere, and a zero result would be an empirical fact about retrieval rather
than an artifact of the arm — the distinction the wiring check cannot supply.

---

## 4. Metric

**Primary: `recall@budget(B = 1920)`** — the fraction of queries whose gold span is hit within the
top-ranked units whose cumulative token count first reaches or exceeds `B`. Every arm gets the
same amount of retrieved **text**, not the same number of **units**.

`recall@5` is sensitive to index granularity, which is precisely the variable this experiment
moves; reporting it alone would measure the confound and call it a result. Tokens counted with
`src.textutil.count_tokens` — one quantity, one procedure (§A5b). Units taken in rank order,
including the one that crosses `B`, then stop. Realised `k` recorded per query per arm.

**`recall@budget` is a new metric in a new experiment. It is not comparable to any published
number and is never printed beside one without that sentence attached.**

**Secondary, every arm:** `recall@5` (legacy comparability), `index_units`, `units_per_doc`,
`token_mean`, mean realised `k`, and **`empty_segments`**. Ranking **hybrid**, scoring variant
**any**, with **strict** as the standing cross-check.

---

## 5. Scoring rung

**S2 (own + absorbed) primary**, matching PW-1; **S3 (own only)** cross-check.

**`S2 ≡ S3` is asserted on the NO-DEDUP arms only** — UNCUT, UNCUT-ws, SEAM — where it holds by
construction. `F@S` and FULL inherit dedup and therefore have absorbed ranges; the assertion would
fire spuriously on them. Halt condition 2 is scoped accordingly.

No arm uses `formatted_naive`, so the inheritance path of `formatted.py:86-94` is not exercised.

---

## 6. Gates

**G6, three parts**, under the final `markers_only: True` configuration —
`tests/test_v16_seam_partition.py`, all passing on 45/45 Track A documents:

1. **whitespace-normalised equality** — concatenated SEAM units reproduce the document character
   for character under the same normalisation on both sides;
2. **exact coverage** — every **non-whitespace** character covered exactly once;
3. **non-overlap** — unchanged.

Plus **the gold-span assertion**: every gold span in the Track A test set overlaps at least one
SEAM `source_range`. Round 1 argued this from ANY-overlap scoring; it is now **VERIFIED**, not
HYPOTHESIS. Part 1 is demonstrated failing against a single substituted word; the gate is
re-checked at m = 384.

**`F@S` regrouping gate** — `tests/test_v16_fas_regrouping.py`. `F@S` must be a **pure
re-grouping** of `F`: no sentence gained, lost or reordered, compared under whitespace
normalisation. **45/45 PASS.** Demonstrated failing in both directions — a dropped unit and a
duplicated one.

**Empty segments — two claims, two tests.** A single test previously asserted a corpus fact under
a behavioural name, so the first corpus with an empty segment would have failed with a message
saying the code padded something when the code was correct and only the corpus differed.

- `test_empty_segment_is_reported_not_padded` — **behavioural, hard on every corpus, forever.**
  The fixture is **constructed**, not waited for: a document whose middle SEAM segments consist
  entirely of sentences dedup removes (2 of 6 empty). Asserts the count is reported, no empty unit
  is padded in, and scoring still proceeds.
- `test_track_a_has_no_empty_segments` — **the Track A measurement, pinned at zero.** If it fires,
  dedup, the corpus or the tokenizer changed — which also means the published C3 corpus is no
  longer what it was.
- **Track B and any other corpus: report and continue.** `empty_segments` is a recorded field of
  every arm, reported whichever way it falls, exactly as `D_ws` is.

---

## 7. Cells

| Cell | Track | Embedder | Role |
|---|---|---|---|
| **A-MiniLM** | A | `all-MiniLM-L6-v2` | **primary, decision-bearing** |
| A-bge | A | `BAAI/bge-base-en-v1.5` | robustness, declared secondary |
| B-MiniLM | B | `all-MiniLM-L6-v2` | exploratory, run last, **non-decision-bearing** |

Embedder pinned **explicitly on the command line and in the frozen JSON**, never inherited from
`config/default.yaml` whose default is bge — Template §B, the single most repeated failure in this
programme. Track B runs only if the cache covers it; **halt and ask** on fresh LLM spend.

---

## 8. Predictions

P1–P5 stand as handed over. P6 and P7 added.

| ID | Prediction | Falsified if | Sighted? |
|---|---|---|---|
| P1 | `D_size(768)` large and positive, ≥ +0.10 on recall@5 | < +0.10, or negative | — |
| P2 | `D_size(768)` shrinks substantially under `recall@budget` | it does not shrink, or grows | — |
| P3 | `D_seam(768)` small, \|D_seam\| ≤ +0.05, CI includes zero | its CI excludes zero | **SIGHTED** |
| P4 | `D_edit(768)` positive but small under `recall@budget`, ≤ +0.05, may not exclude zero | exceeds +0.05, or significantly negative | **SIGHTED** |
| P5 | Under `recall@budget` the UNCUT ordering across 128…768 is flatter than under recall@5 | it is not flatter | — |
| P6 | `D_reseam(768)` small and non-negative under `recall@budget` | significantly negative, or exceeds `D_text` in magnitude | **BLIND** |
| P7 | `D_text(768)` carries the **majority** of `D_edit(768)`, conditional on `D_edit(768)` being distinguishable from zero | `D_text` < half of `D_edit`, or itself indistinguishable from zero while `D_edit` is not | **BLIND** |

**P4 and P7 are the uncomfortable ones and are deliberately so.** If P7 fails — `D_edit` positive
while `D_text` is not — the honest statement is *"the editing pass helps, and it helps by changing
where the cuts fall rather than by improving the text."* That is the opposite of what this
programme has claimed, and it is **reported at the same prominence a confirmation would receive**,
under the frozen `reporting_rule` and `harm_reporting_rule`.

---

## 9. Decision rules — all four branches

**Treatment:** `D_edit`. **Claim under test:** *the formatter's retrieval advantage is
attributable to the editing, not to the segmentation geometry.*

- **ADOPT** — `D_edit` significantly positive on `recall@budget(1920)` in A-MiniLM after Holm
  within `F_EDIT`, **and** directionally positive in A-bge.
- **ADOPT_SCOPED** — significantly positive but confined to exactly one pre-named admissible
  scope. Admissible, enumerated and **closed**: {m = 384 only}, {m = 768 only}, {Track A only},
  {`all-MiniLM-L6-v2` only}, {strict variant only}. A scope not on this list is a HYPOTHESIS.
- **KILL** — not statistically distinguishable from zero in A-MiniLM.
- **REJECT_HARM** — significantly **negative** in A-MiniLM; same rule, sign reversed.

`branch_precedence`: REJECT_HARM over KILL when both could apply; harm is reported as harm, never
as a null. `harm_reporting_rule`: a significant negative gets the prominence a positive would.

**Consequence rules, frozen in advance so the write-up is not a negotiation.** KILL → the paper's
claim is amended to *"better segmentation retrieves better; editing is not separately demonstrated
at matched retrieval budget"*, with readability and verbatim-guardrail results unaffected.
ADOPT_SCOPED → the scope goes in the headline sentence, not a footnote. Under **every** branch,
`D_size` and `D_seam` are reported as first-class results — they are why the experiment exists.

**Holm families, enumerated:**

- `F_EDIT` = { `D_edit(384)`, `D_edit(768)` }, A-MiniLM — **decision-bearing**
- `F_MECH` = { `D_text(384)`, `D_text(768)`, `D_reseam(384)`, `D_reseam(768)` }, A-MiniLM —
  corrected within itself, **not** decision-bearing
- `F_CONFOUND` = { `D_size`, `D_ws`, `D_seam` at both sizes }, A-MiniLM — corrected within itself,
  **not** decision-bearing
- A-bge and B-MiniLM are in **no** family and are not decision-bearing. `S@F` carries no p-value
  anyone acts on.

**`one_shot_rule`:** re-testing `D_edit` on this Track A split after seeing this result is not a
fresh test. A v1.7 must use a different track or a freshly generated corpus.

---

## 10. Halt conditions

1. **G6 fails** in its three-part form under the final SEAM configuration.
2. **`S2 ≠ S3` on a NO-DEDUP arm** (UNCUT, UNCUT-ws, SEAM). Scoped — it does not apply to `F@S`
   or FULL.
3. **Either decomposition identity** fails to hold to exact equality on point estimates — a
   **wiring** check.
4. Any arm's `source_ranges` fall outside `[0, len(doc.text))`, or a no-dedup arm's claimed
   character count exceeds the document length.
5. **Track A triggers any fresh LLM call.** Should now be unreachable; if it fires anyway that is
   a finding about the deterministic path, not a budgeting problem.
6. Track B would trigger fresh LLM spend not served from `cache/`.
7. ~~Published C0 overlap unrecoverable~~ — **does not fire.** G2 established published C0 as
   `U768` at overlap 0.0. It is a **reproduction target, not a comparator**: every decomposition
   term is computed from arms run in this experiment.
8. Anything would be written to `results/`, or to any `posthoc_PW1_*` or `preregistration_*.json`.
9. The bge cell segfaults mid-corpus → use `--sharded-encode` (bit-identical, proven in
   `tests/test_pw1_safe_encode.py`) and record that it was used.
10. Any arm value computed before the pre-registration is committed. Not recoverable — stop and
    report rather than proceeding.
11. **The `F@S` regrouping gate fails**, or the sentence→segment assignment rule is not
    constructible as specified.

---

## 11. Integrity

`Amendment_Criteria_Template.md` at HEAD governs; every §A rule applies by number. The ones that
bite hardest: **§A1** exit status never through a masking pipe; **§A2** per-arm persistence of
per-query vectors *and* per-unit `source_ranges` at the moment they exist, so every arm is
re-scorable without re-encoding; **§A3** long runs verified by `CreationDate`/`CommandLine`;
**§A4** `--out results_v16_<track>_<embedder>/`; **§B** embedder and revision pinned, full native
stack via `_environment()`; **A1d/A1f** exact-equality guards, full-precision inputs, round once;
**A1g** every claim labelled HYPOTHESIS or VERIFIED; **A1h** every mutation verified, not assumed;
**A5b** one quantity one procedure; **PROC-1** every numeric field states its provenance.

**Statistics:** `paired_bootstrap_diff`, `iters = 10000`, `seed = 1337`, `ci = 0.95`, plus
`paired_permutation_p`; `exact_signflip_p` where the outcome is paired binary. Frozen
`boundary_rule`: **a CI bound of exactly 0.0000 does not exclude zero.** Holm within a declared
family only.

**A process finding, recorded and not yet acted on.** A swept parameter (C0's overlap) went
unpersisted and survived only because the metric happened to admit a conservation check. The
candidate rule — *every parameter a sweep selects is persisted in the run manifest, alongside the
value it beat* — is written here and goes to the template **after v1.6 closes**. Governing
documents do not change while an experiment citing them is in flight.

---

## 11b. Disclosure addendum 01 — discoverable from here, not only from the commit log

`preregistration_v16_addendum_01.json` augments the freeze (`1b01f9b`, 2026-07-31T10:06:54Z)
without modifying it. It exists because `prior_knowledge_at_freeze` recorded the three published
768 values but **not** a second body of knowledge held before the freeze: a component ledger read
off the published ablation table, and the principal's expectation formed from it. That knowledge
lived in conversation, which is not a committed artifact — **so nothing in the repository would
ever have revealed it.**

The ledger, as exact integer counts over n = 176 (published, Track A, MiniLM, hybrid, any,
recall@5): C0 138, C3-markeronly 140, C3-noref 137, C3-nodedup 146, C3 144, C2 150, C5 150. By
subtraction — **no CI, no test, not a v1.6 quantity** — seam +2/176, full pass over baseline
+6/176, reference resolution +7/176, dedup **−2/176**, and contextual over formatter **+6/176**.

The principal's expectation at freeze: that the advantage is small — *on the order of six queries
out of 176*, which is exactly +6/176 — that whatever is real in it sits in **reference
resolution**, that **dedup may cost slightly**, and that `D_edit` may come back indistinguishable
from zero.

**Chronology:** P6 and P7 were formed at `4851f58`, before the ledger existed; the ledger formed
after `d43063f` and before the freeze; no arm value has been computed at any point. So the ledger
did not inform the predictions' formation but *was* knowledge held at freeze. P6 and P7 stand
exactly as sealed and remain **BLIND**, with the addendum attached to that marking rather than
replacing it.

The addendum is **not** cleanly orthogonal to P7 and says so: "the benefit is concentrated in
reference resolution" leans the same way P7 does. A reader may weigh that themselves.

**The addendum alters no prediction, arm, decision rule, family, metric or halt condition**, and
carries the bound that makes the mechanism safe: *a disclosure addendum is permitted only before
the first arm value exists, and only to ADD. Anything touching a prediction, arm, rule, family,
metric or halt condition is not an addendum — it is a new pre-registration, and a new experiment
under the one-shot rule.*

---

## 12. Order of operations

1. ✅ Gate 0, three rounds.
2. ✅ This plan.
3. `preregistration_v16.json`, every field populated, no placeholders.
4. ✅ G6 and `F@S` gates written and run — they touch no arm value.
5. **Commit plan + pre-registration. Record commit hash and UTC timestamp.**
6. Then `scripts/segment_size_sweep.py`.
7. Run A-MiniLM. **Record the UTC timestamp of the first arm value and state the interval from
   the freeze commit** — the programme's precedent is 37 minutes.
8. A-bge, then B-MiniLM.
9. `Results_v16_SegmentSize.md`: predictions scored line by line, then the branch named.
10. **Do not touch the white paper or the brief.** The wording change, if any, is Shamik's call.
