# v1.7 Gate 0 — rulings on F1–F5, and the freeze instruction

**Responds to:** Gate 0 build at `235a59d`; 52 v17 tests, full suite 217 green; plan
deliberately untracked pending these rulings.
**Date:** 1 August 2026
**Status:** rulings on all five findings. F1 and F3 are one-token/one-line amendments; F2 is
decided here and changes the package builder; then freeze. Holding the plan untracked until
these were ruled was correct — a freeze that would have sealed a false sentence and an
unrunnable design is exactly what the pre-freeze check exists to catch.

---

## 1. F1 — S1 was the wrong rung, and the error is mine in a familiar shape

Ruling: **replace S1 with S3** in §2.2. One token, as recommended.

The error is worth classifying, because it is the same generative failure item 7 names, in
apparatus form: I wrote "S1 reported" from memory of *a* scoring ladder rather than from the
ladder this rebuild actually has. S1's inherited term belongs to PW-1's TightUnit
construction; v1.6's arms yield own, absorbed, and their sums — S2 and S3. A rung asserted
from a remembered apparatus rather than the present one, caught by grepping the code, which
is precisely the "procedure run against the final object" remedy. S3 is also the right
substitute on the merits: it is the conservative floor v1.6 actually reported, so the two
experiments' descriptive companions stay comparable.

---

## 2. F2 — ruled: per-query matched budget, and every query stays

None of the four listed options is taken. Ruling: **B2 becomes B2(q), a per-query matched
budget:**

> **B2(q) = max(1024, T_a(q) over every arm `a` included in E2 on that track)**, where
> T_a(q) is the token length of arm `a`'s minimal gold-covering unit set for query `q`.
> Every arm's package for query `q` is built to exactly B2(q) tokens, by the §3.1 padding
> procedure unchanged.

The design's one non-negotiable guarantee is **equal tokens within each pair**, because the
comparison is paired per query — nothing requires the budget to be a global constant, and
the plan conflated the two. B2(q) is deterministic from the frozen inventories, symmetric
across arms, fixed before any generation, and outcome-independent. It is the same shape as
recall@budget: the budget is set by rule, not by result.

Why not the four:

- **Raise B2 globally:** Track A's max (1444) forces ≥1536; Track B's (3840) forces ≥4096.
  A worst-case-driven constant pads the ~96% of queries that fit at 1024 with extra
  neutral material, shrinking the treatment's share of every package and washing the
  contrast toward null for the majority to accommodate the tail.
- **Symmetric exclusion:** worse than it looks, and not because of arm bias — the exclusion
  is paired and the subpopulation comparison would be valid. It is that the excluded
  queries are exactly the ones where gold straddles fixed cuts, i.e. **the
  mechanism-carrying cases** — the queries E1's `integrity_single` penalises `U768` on and
  the reading claim is about. Excluding them tests reading only where packaging barely
  differs. It also guts Track B (n=89), the one real-prose corpus.
- **Let packages exceed B2 asymmetrically:** reintroduces unequal tokens within a pair,
  which is the size confound this entire programme exists to remove. Not considered
  further.
- **Track A only:** forfeits the deployment-relevant corpus to preserve a constant that
  §3.1 never actually needed.

Consequential amendments, to be made before the freeze:

- §3.1 restated with B2(q); the sentence "both arms hand the generator the same number of
  tokens" becomes "the same number of tokens **per query**".
- `GoldExceedsBudget` is retained as an assertion, now against B2(q) — unreachable by
  construction, so any raise is an APPARATUS-STOP, which restores the "impossible by
  construction" sentence to truth instead of deleting it.
- **Cap:** B2(q) > 8192 is an APPARATUS-STOP (nothing known approaches it; if it fires,
  diagnose, don't accommodate).
- New required tests: within-pair token equality as a property across arms; B2(q) = 1024
  when gold fits; an escalation case (straddling gold → B2(q) = T(q), all arms padded to
  it); the cap STOP.
- New descriptive reporting in `Results_v17_E2_Reading.md`: the distribution of B2(q) per
  track, and the count of queries with B2(q) > 1024, attributed to the arm whose T_a(q)
  set it. Recorded beside the primary result, because a reader must be able to see how
  often the budget escalated and why.

One discipline note: the probe table in the findings (6/176, 61/150, the medians and
maxima) did its job — it informed design before the freeze, which is what pre-freeze
diagnostics are for. **It is not a result.** The same quantities fall out of E1's declared
feasibility ceilings, measured under the frozen procedure; those are the numbers that get
reported, and the probe's are not to be quoted in any results document.

---

## 3. F3 — unwrapped is correct, and canonical form is settled now

Ruling: the agent's reading stands — nobody chooses a mid-sentence newline; the wrap was my
markdown line-width, not prompt design. Flagging rather than silently settling was right:
"frozen verbatim" is exactly where an interpretation must be visible.

To prevent the next dispute of this kind: **the prompt file frozen in the Gate 0 commit is
the canonical object; the plan's fenced block is a rendering of it.** The plan's block is
amended to the unwrapped form before freeze, and a sentence is added: where the plan's
markdown and a frozen artifact differ in line-wrapping or whitespace, the artifact is
canonical; any *semantic* divergence between them is an APPARATUS-STOP, not a choice.

---

## 4. F4 — endorsed, and it goes in the results document as a control

Multi-document gold 0/176 and 0/150, zero-length spans likewise, with both classes still
defined and tested in code: correct practice — a metric must be total over its input domain,
not over the inputs the corpus happens to contain. Record both zero-counts in
`Results_v17_E1_Integrity.md` as controls that earned their place by coming back empty, the
`D_ws = 0` pattern from v1.6.

---

## 5. F5 — acknowledged under A1f, and the bug's family is worth one sentence

The checker's `dev_fraction or 0.2` turning Track B's declared 0.0 into 0.2 is the falsy-
zero default, and it is the same species as the overrides this programme has met before: a
fallback that silently replaces a legitimate zero. The plan was right, the probe was wrong,
you said so unprompted, and the exact-expression check settled it — A1f honoured in full.
No code change ordered; one suggestion, not an instruction: probe scripts take defaults via
an explicit `is None` sentinel, so a declared zero can never be overridden again.

---

## 6. Freeze instruction

1. Amend the plan: F1's token (S1 → S3), F2's §3.1 restatement with B2(q), cap, and
   reporting additions, F3's unwrapped block and canonicality sentence. Add a short
   **"Pre-freeze amendments"** note to §0 listing the three with their finding IDs — the
   repo history would show the differences anyway; the note makes them legible rather than
   discoverable.
2. Update and extend the tests per §2; full suite green.
3. **One commit: plan + code + prompt file + normalisation + tests. That commit is the
   freeze.** Any wording change after it is a new pre-registration, per the plan's own
   terms.
4. Then E1 in cell order — A-MiniLM, A-bge, B-MiniLM — and STOP at Gate 1 with
   `Results_v17_E1_Integrity.md`.

Confirmed on this side: nothing spent, no arm value exists, closed artifacts untouched at
`235ccfb` / `cdd197f` / `12483f9` / `1b01f9b`. The five open decisions on Shamik's queue are
unaffected by anything in this ruling.
