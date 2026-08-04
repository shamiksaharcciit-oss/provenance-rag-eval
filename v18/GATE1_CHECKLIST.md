# v1.8 Gate 1 — assembly checklist, compiled from the artifacts

**Compiled:** 1 August 2026, while Batch J1 was collecting — before any results writing.
**Method:** each requirement below was read out of the named artifact at the cited location, not
recalled. That is item 7 applied to the checklist that governs the document item 7 will be
applied to; the rule this experiment now enforces structurally is not one the reporting document
gets an exemption from.

---

## 0. Attribution correction, recorded before it can be lost

The session report took ownership of the **G14 specification failure**. That is wrong and the
record is corrected here rather than in memory:

- The `custom_id` grammar that could not express the call plan — seven fields, `{rep} ∈ {0,1,2}`
  — was specified in **`Decisions_v18_G12_2026-08-01.md` §1**, by the ruling side.
  `Decisions_v18_G14_2026-08-01.md` §4 assigns it there explicitly: *"this one is mine with the
  census in plain sight."*
- The agent's error at G12 was the **alphabet half of the API constraint** — asserting
  `custom_id`'s 64-character limit while never validating its character set. That is owned at
  G12 and does not transfer forward.

**Therefore:** when the results document's amendments table cites G14/PF-15, the specification is
attributed to `Decisions_v18_G14_2026-08-01.md` as written. Taking on an error that is not one's
own corrupts the record exactly as much as shedding one that is.

## 1. Gate 1 contents — from the frozen plan, §9 "Gate 1 — data complete"

- [ ] predictions scored **against sealed text**, on **named cells only**
- [ ] the three-instrument table, **per track**
- [ ] `F_BIAS` = **B1 alone**, with single-member Holm **stated as the identity it is**
- [ ] all descriptive companions **with discordant counts**
- [ ] the **probe disposition** — abandoned by rule, determinism unmeasured, every single-run
      number caveated
- [ ] costs **actual vs projected against the ledger**
- [ ] limitations: non-blindness, single judge, fixed-k-by-design, **the unavailable temperature
      pin**
- [ ] **item 7 self-check with its output in the record**
- [ ] then **STOP** — no packaging, no release drafting, no sequencing recommendation

## 2. PF-14 §3 disclosure — from the plan, "Declared narrowing [PF-14]"

- [ ] state that the repeats cover the **joint** generation-and-judge draw, and that judge
      variance and generation variance are **not separately identified** — stated, not implied

## 3. PF-15 — from the plan's §0 amendments table, row PF-15 (verbatim)

- [ ] amendments table carries PF-15 with **G14** as its finding and
      `Decisions_v18_G14_2026-08-01.md` as its authority (see §0 above)
- [ ] the entry as frozen: *the identity collapsed two orthogonal coordinates — which answer a
      judgement concerns and which sub-call within a metric — so the grammar could not express
      the call plan (`cp` makes 5 calls, `ar` 9 on the targeted pair); an eighth field is added
      and the validity set is derived from the frozen call plan*

## 4. Item 7 — from `Candidates_ScopeOfDirectionTest_2026-07-31.md` §5 (the boxed statement)

> A claim a document makes about **its own contents**, where that claim is a count or a
> universal, must name the procedure that produced it — the list counted, the search run — and
> that procedure must be executed against the **final** text rather than the remembered one.

§6 records the open question of whether it generalises beyond self-description; the general form
offered there — *any count or universal a document asserts over material fixed at the time of
writing* — is the safer standard and is the one this document will meet.

- [ ] every count and universal names its procedure
- [ ] every such procedure is **executed against the final text**, not the draft
- [ ] the check's **output** goes in the record (appendix or commit message)

## 5. Predictions to score — sealed text, named cells (plan §5)

| id | cell named in the sealed text | how scored |
|---|---|---|
| **PD-1** | Track A, descriptive | context-level metrics favour `F768` over `U256` at fixed k |
| **PD-2** | **both tracks**, descriptive [PF-7] | direction comparison: `U768 − U256` at least as large as `F768 − U768` on the context composite; never tested |
| **PD-3** | Track A, `F_BIAS`'s single member B1 | the tested member |
| **PD-4** | Track A, descriptive, **control** | token-F1 `F768 − U768` ≈ 0; `F768 − U256` may be positive |
| **PD-5** | **Track B**, direction only | B1's sign on Track B matches Track A's |

Pre-committed interpretations (plan §5) are carried verbatim; neither branch reopens v1.6.

## 6. Conduct boundaries still live between here and Gate 1

- **J1 collection:** reads are **row counts, model constancy, resubmission triage only**. The
  source-inspection test guards the builder; the collection step is guarded only by the agent.
- **J2 construction:** reading J1's extraction outputs is **construction, not peeking** —
  statement lists in, prompts out, **no numbers derived**.
- No F1, no judge-score aggregation, no per-arm signal assembled before the results stage.
