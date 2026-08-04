# Memory exhaustion: go ahead, with one trap to avoid

2026-07-30 · `2bdca33` · fault diagnosed, fail-stop confirmed, four batches banked

**Yes to `wsl --shutdown`, and close Firefox too.** Check nothing unsaved is running inside WSL
first — that is the only reason to hesitate, and it is a ten-second check. The arithmetic supports
your expectation: freeing ~4 GB from `vmmemWSL` and ~1.9 GB from Firefox against 393 MB free of
7,739 MB gives roughly 6 GB of headroom, and bge-base at batch 64 needs a small fraction of that
for peak activations. It should encode immediately.

Agreed that §6 is moot. This was never a machine that cannot run bge.

---

## 1. The trap the diagnosis creates

The single most useful line in your report is also the most dangerous one: *"batch 8 succeeded 4/4
where batch 64 failed 8/8."*

That makes the wrong fix look obvious. **Do not lower the batch size to fit the memory.** Batch
size determines padding, padding determines the activations, and the entire bit-identity property
of `safe_encode` rests on every batch containing exactly the set it contained in the monolithic
path at the published batch size. Encoding bge at batch 8 would work, would be fast, and would
silently reintroduce the deviation label, the measurement block, the margin analysis and the
mixed-path `r` — the whole apparatus you spent yesterday making unnecessary.

Free the memory instead. It is the fix that preserves the property.

Flag it in `safe_encode` if it is not already: the batch size should be a checked invariant
against the published configuration, not a tunable parameter, so that nobody — including you at
2 a.m. — can make this trade without the code objecting.

---

## 2. §1 did more work than either of us framed it as doing

I proposed the one-batch probe as a check on whether `run-20260726-191447` could have been
silently corrupted. It answered that. But its more important consequence is the one that lands
today: **fail-stop is what makes checkpoint-resume sound at all.**

If the fault could corrupt silently, every banked batch would be suspect, resume would splice
possibly-wrong rows into the matrix, and the completeness assertion would pass over a corrupted
result. The strategy would have been unusable. Because the fault is fail-stop, a batch that
completed is a batch that is correct, and your four banked batches are trustworthy.

Worth recording that dependency explicitly next to the checkpointing code, because it is a load-
bearing assumption that is currently only true by evidence, not by construction. If anyone later
sees crashes from a *different* cause, the fail-stop finding does not automatically transfer and
the banked batches would need re-deriving.

---

## 3. Make it not recur

The pressure will rebuild. WSL restarts on next use and grows back, uptime is six days, and the
machine has 7.7 GB total — this is a standing condition, not an incident.

- **Cap WSL in `.wslconfig`** (`memory=2GB`, or whatever your WSL work actually needs). One-line
  durable fix, and it prevents the same diagnosis being rediscovered in three weeks.
- **Run the bge encode as the only heavy thing on the box.** Eight batches, one-time cost, then
  every arm is a re-score.
- **Re-check free memory before each grind session** and record it beside the checkpoint. If a
  batch fails, you then know whether it was pressure or something new, without re-running the
  whole diagnosis.

---

## 4. The record needs a pass now that the story is complete

Three layers of correction are sitting in the repo, and the final answer supersedes all of them.
Rather than leaving a reader to reconstruct the sequence, write one coherent account:

- **`BLOCKED / ENVIRONMENT` is now diagnosed**, not blocked-and-unexplained. Update it with the
  actual cause, the Event Viewer counts, and the resolution.
- **`BLOCKED / PLATFORM SUSPECT` should not survive.** I proposed it when hardware was live; WHEA
  is clean and the cause is mundane. Leaving a "platform suspect" state in the record when the
  platform is fine is its own kind of misleading.
- **E-5 gets the final version**: not a version regression (falsified), not hardware (ruled out by
  WHEA), memory exhaustion (confirmed by 40 Resource-Exhaustion events escalating across 07-26 to
  07-30, and by the batch-size dependence).
- **My thermal hypothesis was wrong and is in the repo**, in the document you committed. A1g
  applies to my files as much as your commit messages — it should be labelled as the hypothesis it
  was. I would rather it stay visible and marked than be tidied away.

Your three-tier framing is the part that stands, and it is now better supported than when I
proposed it: there is no mechanism by which an allocation failure perturbs a completed encode. The
middle tier's caveat is close to closed on mechanism alone, and will close entirely if the bge
cells reproduce.

---

## 5. One process finding worth adding to the template

Neither of us read the platform's own diagnostic log until several rounds in. Between us we
proposed a version regression (wrong), reconstructed the pin forensically (useful, but it
falsified the hypothesis rather than confirming it), and floated thermal degradation (wrong) —
while Event Viewer had been recording the correct answer forty times since 07-23.

The rule: **when the platform misbehaves, read the platform's own record before constructing a
mechanism.** It is cheap, it is exhaustive in a way hypothesising is not, and it beats reasoning
from symptoms whenever the system already writes down what happened. That belongs beside A1e–A1g
as a diagnostic-order rule rather than an authoring rule — call it A1h if the numbering suits.

I raised Event Viewer eventually and after two wrong mechanisms of my own, so this is a shared
finding rather than one I am handing you.

`ast.parse` catching the NUL bytes is the same family as asserting before the write — validate the
artifact at the moment it is produced, not at the moment it is used. That habit has now caught two
different classes of self-inflicted damage in two days.

---

## In order

1. Check nothing unsaved is in WSL, then `wsl --shutdown`, then close Firefox.
2. Confirm the batch size is a checked invariant, not a parameter.
3. Grind the remaining four batches. Record free memory beside each.
4. `.wslconfig` cap so this does not recur.
5. Record pass per §4.

If the bge cells reproduce 0.6080 / 0.7557 and 0.3600 / 0.4267, guard 1 closes 8/8 on the
unchanged path with no qualifier, and B5 has every input it needs.
