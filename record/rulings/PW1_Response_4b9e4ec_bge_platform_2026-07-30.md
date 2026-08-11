# bge is not encodable here: what to do, in order

2026-07-30 · `4b9e4ec` · guard 1 at 6/8 · B3 passed · errata complete at five entries

Your correction is right and I'd sharpen it further: this stopped being a workaround problem and
became a platform problem. But two things in your report set the bar higher than it needs to be,
and one of them means the silent-corruption question is answerable in about two minutes with what
you already have.

**Do §1 before you reboot.** Once the machine is restarted you may not be able to reproduce the
fault at all, and the chance to characterise it while it is live will be gone.

---

## 1. The determinism probe needs one batch, not a complete run

You reported the probe as failing because batch 2 of 2 never completed. But the question — *can
this fault corrupt silently instead of crashing?* — does not need a complete run of anything. It
needs **any single batch encoded successfully twice**, and compared.

Take the smallest batch that has ever succeeded. Eight texts is fine. Encode it repeatedly with
retry, discard the crashes, keep every success, and compare all successes pairwise with
`np.array_equal`.

- **All successes identical** → the fault is fail-stop: it crashes or it is correct, and there is
  no third behaviour observed. That is the good case, it is the case your evidence so far is
  consistent with, and it closes the worry I raised about `run-20260726-191447` to the extent
  anything can while the machine is in this state.
- **Two successes differ** → silent corruption is proven, and everything computed on this machine
  is in question, including MiniLM. That would be a much bigger finding than a blocked cell, and
  you would want to know it now rather than after B5.

This is runnable on a degrading machine precisely because it needs tiny successful encodes rather
than a lucky complete one. The 8/8 failure streak is not an obstacle to it — it just means more
attempts.

---

## 2. Make the encode resumable — this is the structural fix

Your sharding isolates batches but, as far as I can tell from the report, a crash loses the whole
run. That is what makes a complete encode require a lucky uninterrupted session.

**Checkpoint each batch to disk as it completes, and skip completed batches on restart.**

The requirement then changes from "every batch must succeed in one session" to "**each batch must
succeed once, ever.**" With 238 and 235 texts at batch 64, that is eight batches total. On a
machine that sometimes succeeds and sometimes fails 8/8, eight one-time successes are achievable
by grinding — across retries, across reboots, across days if necessary — whereas a lucky complete
run may never arrive.

Two details worth getting right: key each checkpoint by the batch's content hash plus the model
revision, so a resumed run cannot silently splice batches from different states; and assert the
full set is present and correctly ordered before unsorting, so a partial resume fails loudly
rather than producing a short matrix.

This also gives you §1 for free: while grinding, encode one batch twice deliberately and keep both.

And note what it buys downstream — you need bge's embeddings for family 1 exactly **once**. After
that, retrieval results persist and every arm is a re-score. The expensive, fault-exposed step is
a single one-time cost, not a per-arm cost.

---

## 3. Then reboot — and treat idle time as part of the treatment

Yes to the reboot, after §1. One addition: if the degradation is thermal, a reboot alone may not
be enough — the machine needs to sit cool for a while, not just restart. Give it real idle time
before the first attempt, and note how long, because "worked after 20 minutes cool, failed again
after 15 minutes of load" is a diagnosis and "worked after reboot" is not.

Your three observations — model-size dependence, intermittency, and a failure rate that climbs
across a session — fit thermal or hardware degradation at least as well as they fit software
resource exhaustion. The discriminator is that fresh subprocesses are failing more over time:
per-process leaks should reset at process boundaries, so an escalating rate under process isolation
points at system-level state, not process state.

---

## 4. The blast radius is narrower than "no bge number is established"

I would not let that sentence stand unqualified in the record, for two reasons.

**There is a positive control for this machine, from today.** Guard 1's family-1 MiniLM re-runs
reproduced 0.5682 / 0.7216 and Track B's levels **exactly**, on this box, in this session. If the
machine were silently corrupting computation in general, exact reproduction of published levels
across a full re-run would be unlikely. That bounds the fault: it correlates with the larger model
and the heavier load, and the machine can still compute MiniLM correctly today.

**The published bge numbers are unverified, not unsupported.** They are not established *by
reproduction* — you are right that re-scoring persisted retrieval cannot speak to whether the
encoding was correct, because it faithfully reproduces whatever the embeddings were. But they are
internally coherent in a way corruption does not usually produce: bge sits slightly above MiniLM
on Track A, which is what a 768-dim model should do, and the pattern holds across six conditions
plus the ablations plus the size-matched control. Corruption produces noise, not a clean ordering
that happens to match the expected geometry.

So the honest record is three-tiered, and the results document should say it in these terms:
MiniLM's numbers are **verified by reproduction on this machine**; bge's composition numbers are
**verified as re-scorings but unverified at the encoding step**; family 1's bge cells are
**unobtained**. Collapsing those into "no bge number is established" understates the first two and
is the kind of over-correction that reads as scrupulous now and misleading later.

Worth a new state alongside `BLOCKED / ENVIRONMENT`, since the situation escalated: something like
`BLOCKED / PLATFORM SUSPECT`, carrying the scope statement above. A reader six months out needs to
know not just that something was blocked but how far the doubt reaches — and, equally, where it
stops.

---

## 5. Hardware checks, now worth doing properly

Event Viewer for `0xC0000005` and WHEA since 2026-07-23, yes — attempt it, and if it needs
elevation that is a two-minute ask rather than a blocker. Add: Windows Memory Diagnostic on the
next restart (it runs pre-boot, so it costs one reboot cycle you are taking anyway), machine uptime,
and thermal throttling if you can read it.

Record the negative results. A `PLATFORM SUSPECT` entry with no diagnostics behind it invites
exactly the question you cannot answer later.

---

## 6. A second machine is better evidence, not just a workaround

If this box cannot be made to encode bge reliably, moving is the answer — and it is worth framing
correctly, because it is an upgrade rather than a concession.

Reproducing the published bge levels on **independent hardware** is stronger verification than
reproducing them on the machine that produced them. It removes the shared-machine-state
explanation entirely, which is the very explanation currently in play. If cross-machine
reproduction gives 0.6080 / 0.7557 and 0.3600 / 0.4267, guard 1 closes with better evidence than
the original plan would have produced.

This is also where C-2 pays for itself. You now capture `torch`, `transformers`,
`sentence-transformers`, `tokenizers`, `safetensors`, `huggingface_hub`, the threading env vars and
`parallel_info()` — which is enough to reconstruct the environment somewhere else and know that you
did. Two days ago you could not have moved machines without introducing an unpinned variable.

The obvious constraint would be confidentiality if an internal corpus were ever in scope: such
data would not be movable to arbitrary compute. (None is — this project is personal work on
synthetic and public data; the note is kept for the record of what was considered.)

---

## 7. If none of it works

The fallback is (b): family 1's aggregate from MiniLM/A alone. My view is unchanged that this is
expensive, and §2's checkpointing means you should not reach it quickly — eight one-time batch
successes is a low bar to clear given enough attempts.

But if you do reach it, the description that goes in the results document is now better than it
would have been an hour ago: not "bge failed," but *the bge cells were blocked by a platform fault
that is characterised, diagnosed, and recorded, on a machine whose MiniLM computations reproduce
exactly, with the encoding step being the single unverified link.* That is a real, defensible
account of a limitation rather than an absence.

---

## 8. On §5 and §6

`ContradictoryCell` is a better find than the one I asked about. `delta_full == 0.0` declared
significant is genuinely contradictory input, and a `TypeError` surfacing three branches from its
cause is the failure mode that costs the most to debug at the worst moment. Refusing it by name at
the boundary is right, and "one branch-sweep away from firing" is the accurate assessment.

A1g plus E-5 plus the `BLOCKED / ENVIRONMENT` record is the correct disposition, and leaving the
commit message wrong is the point — a rule that let you quietly amend the record would not be the
rule.

---

## In order

1. The one-batch determinism probe, **before the reboot**.
2. Add per-batch checkpoint/resume to `safe_encode`.
3. Reboot, with real idle time. Note the timings.
4. Grind the eight batches with resume and retry. Encode one twice while you are at it.
5. Event Viewer and Memory Diagnostic; record negatives.
6. In parallel, find out whether a second machine is available.

Everything not touching bge stands: guard 1 at 6/8, B3 passed, errata complete, arm inputs
persisted. B5 can run on the six cells that have inputs whenever you want it to — the two bge
family-1 cells are the only thing waiting on any of this.
