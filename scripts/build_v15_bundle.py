"""Build the v1.5 evidentiary bundle and verify it (handoff 2026-07-29 §7a).

Ships the four sources pinned by `hashes_at_freeze` alongside the plan, prereg, results and
artifacts, so the pins are checkable from what was shipped rather than on trust.

Sources are shipped **as run** — read from the run commit, not the working tree — because the
working tree has since gained post-run corrections. Where an as-run file disagrees with its
pin, the MANIFEST says so per file rather than quietly shipping something that fails a check
the reader is invited to perform.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AS_RUN_COMMIT = "dbef489"          # M7 v1.5 RESULT — the tree that produced the artifacts
OUT = ROOT / "rag_formatter_v1.5_smalltobig_REJECT_HARM.zip"

# Current working-tree state: these carry the post-run corrections and MUST be the live
# versions. None of them is pinned by `hashes_at_freeze` (the prereg is the pinning document).
DOCS = ["preregistration_v15.json", "preregistration_v14.json",
        "Results_v1.5_SmallToBig.md", "ARCHIVE_MANIFEST.md"]
# Pinned by `hashes_at_freeze`: shipped AS RUN so a reader can verify the pins against what was
# shipped. The working tree has moved on — the template has since gained rules generalised from
# this very run, and shipping that version would break a check the MANIFEST invites.
PINNED_AS_RUN = ["Experiment_Plan_v1.5_SmallToBig.md", "Amendment_Criteria_Template.md",
                 "src/smalltobig/retrieve.py", "src/smalltobig/chunker.py",
                 "src/smalltobig/units.py", "config/default.yaml"]
# Code the results document and MANIFEST refer to by name. Shipped from the WORKING TREE,
# because these are the corrected post-run versions the document actually cites — a bundle that
# names a negative control and does not carry it describes evidence it has not supplied.
CODE = ["src/stats/tests.py", "scripts/merge_v15.py", "scripts/build_v15_bundle.py",
        "scripts/check_blurb_ratio.py", "tests/test_exact_signflip.py",
        "tests/test_persistence_survives_kill.py"]
DIRS = ["results_v15_merged", "results_v15_A", "results_v15_B",
        "results_v15_B_C4_128", "results_v15_B_C0_256",
        "results_v15_B_C2_256", "results_v15_B_C4_256"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def as_run(path: str) -> bytes:
    """The file as it was when the run produced these artifacts.

    Git stores LF; the working tree is CRLF. Return whichever form matches the working tree's
    convention for that file, so a reader hashing the shipped file gets the same value the
    working tree would give for identical content.
    """
    blob = subprocess.run(["git", "show", f"{AS_RUN_COMMIT}:{path}"],
                          cwd=str(ROOT), capture_output=True, check=True).stdout
    wt = (ROOT / path).read_bytes()
    if b"\r\n" in wt and b"\r\n" not in blob:
        blob = blob.replace(b"\n", b"\r\n")
    return blob


def main() -> int:
    prereg = json.loads((ROOT / "preregistration_v15.json").read_text(encoding="utf-8"))
    pins = prereg["hashes_at_freeze"]

    members: list[tuple[str, bytes]] = []
    for d in DOCS:
        members.append((d, (ROOT / d).read_bytes()))
    for s in PINNED_AS_RUN:
        members.append((s, as_run(s)))
    for c in CODE:
        members.append((c, (ROOT / c).read_bytes()))
    for d in DIRS:
        for p in sorted(q for q in (ROOT / d).rglob("*") if q.is_file()):
            members.append((p.relative_to(ROOT).as_posix(), p.read_bytes()))

    # Pin verification, reported per file — including the one that fails.
    pin_lines, failures = [], []
    for name, expect in pins.items():
        shipped = next((data for n, data in members if n == name), None)
        if shipped is None:
            pin_lines.append(f"  NOT SHIPPED  {name}")
            failures.append(name)
            continue
        got = sha(shipped)
        ok = got == expect
        pin_lines.append(f"  {'VERIFIED    ' if ok else 'MISMATCH    '}{name}\n"
                         f"      pinned  {expect}\n      shipped {got}")
        if not ok:
            failures.append(name)

    merged = json.loads((ROOT / "results_v15_merged/results.json").read_text(encoding="utf-8"))
    v = merged["verdict"]

    lines = [
        "v1.5 Small-to-big / parent-child retrieval (M7) — REJECT_HARM",
        "created_utc=2026-07-29T00:00:00Z  (re-cut after the 2026-07-29 corrections)",
        "", f"decision={v['verdict']}", f"decision_rule={v['rule']}", "",
        f"prereg=preregistration_v15.json  frozen_utc={prereg['frozen_utc']}",
        f"superseded=preregistration_v14.json  status={json.loads((ROOT/'preregistration_v14.json').read_text(encoding='utf-8'))['status']}",
        "", f"p_value_method={merged['p_value_method']}", "",
        "significant_harms (Track A, secondary / no-harm check, n=176):",
    ] + [f"  {s}" for s in v["significant_harms"]] + [
        "", "significant_gains (Track B, primary, n=150):",
    ] + [f"  {s}" for s in v["significant_gains"]] + [
        "",
        "K is the discordant-pair count — the sample size each paired binary test actually runs",
        "on. p-values are exact enumerations of the pre-registered sign-flip null, not 10k",
        "Monte-Carlo estimates; the estimates are retained in results.json as p_mc_10k.",
        "",
        "NOTE ON C2@128: significant by the exact test at p=0.049042, a margin of 0.001. The",
        "first release reported it marginal at a sampled p=0.0524. Significant, not robust.",
        "",
        "NOTE ON THE CRITERIA: the frozen significant_definition names two procedures ('paired CI",
        "excludes 0' and 'after Holm') which disagree on C2@128 and C2@256 once the CI is",
        "multiplicity-adjusted. Holm governs. REJECT_HARM holds under every reading. Listed in",
        "results_v15_merged/results.json under verdict.criteria_disagreements.",
        "",
        "NOTE ON PRECEDENCE: Track B's significant-positive set is {C0,C2,C4} at both child sizes,",
        "so the frozen outcome table read alone gives ADOPT. ADOPT requires H7a clean (no harm on",
        "Track A) and it is not. The frozen branch_precedence clause therefore applies: one",
        "significant harm on the secondary track overrides six significant gains on the primary.",
        "Honoured as frozen; the design question it raises is recorded as a finding, NOT as a",
        "change to the rules.",
        "", f"holm_family={merged['holm_family']}", f"recompute_note={merged['note']}",
        "  recomputation is scripts/merge_v15.py, from the persisted per-query vectors",
        "  (vectors.json); no model was re-run and no measured quantity changed.",
        "", "PINNED SOURCE VERIFICATION (hashes_at_freeze):",
    ] + pin_lines + [
        "",
        "  Every pinned file is shipped AS RUN, read from commit " + AS_RUN_COMMIT + ", not from",
        "  the working tree — which has since moved on: chunker.py gained blurb_dilution, and",
        "  Amendment_Criteria_Template.md gained rules A2b and A5-A8 generalised from this run.",
        "  Shipping the current versions would break the very check this section invites.",
        "",
        "  chunker.py MISMATCHES its pin and this is a real defect, disclosed rather than hidden:",
        "  the pin records the freeze commit d5953fa, and the file was rewritten 49 minutes later",
        "  in d13216e (+166/-87) to IMPLEMENT the sentence-aligned child rule that plan section 3",
        "  mandates. The code that ran is not the code that was pinned. See the errata block in",
        "  preregistration_v15.json and ARCHIVE_MANIFEST.md.",
        "",
        "CODE SHIPPED (working-tree versions — the corrected post-run ones the document cites):",
        "  src/stats/tests.py                          exact_signflip_p + the equal-magnitude guard",
        "  scripts/merge_v15.py                        recomputes all 12 cells under the frozen family",
        "  scripts/build_v15_bundle.py                 builds and verifies this bundle",
        "  scripts/check_blurb_ratio.py                the blurb-attachment diagnostic (cache-only)",
        "  tests/test_exact_signflip.py                11 tests incl. two negative controls",
        "  tests/test_persistence_survives_kill.py     the section A2 kill-mid-run control + the",
        "                                              write-at-end violation arm",
        "", "artifact roles:",
        "  results_v15_merged/   authoritative statistics — exact p, Holm over the frozen family",
        "  results_v15_A/        Track A, all six cells, one process",
        "  results_v15_B/        Track B, C0@128 and C2@128",
        "  results_v15_B_*/      Track B remaining cells, run in isolated processes after segfaults",
        "  per-condition results.json/per_query.jsonl/vectors.json written after EVERY condition",
        "  (template section A2 — an earlier write-at-end version destroyed six completed Track A",
        "  cells; the kill-mid-run negative control for that guard is",
        "  tests/test_persistence_survives_kill.py)",
        "",
        "NOT retested here, by standing decision: the reranking axis and identity injection are",
        "spent on this A/B split. No published number in the white paper is amended by this",
        "bundle, and M7 is by decision not cited in the paper.",
        "", "file hashes (sha256):",
    ] + [f"  {sha(data)}  {name}" for name, data in members]

    manifest = "\n".join(lines) + "\n"
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members:
            z.writestr(name, data)
        z.writestr("MANIFEST.txt", manifest)

    # ---- verify what was just written ----
    z = zipfile.ZipFile(OUT)
    assert z.testzip() is None, "zip CRC failure"
    claimed = {p[1]: p[0] for p in
               (ln.split() for ln in z.read("MANIFEST.txt").decode("utf-8").splitlines())
               if len(p) == 2 and len(p[0]) == 64}
    names = [n for n in z.namelist() if n != "MANIFEST.txt"]
    assert set(names) == set(claimed), f"manifest/zip mismatch: {set(names) ^ set(claimed)}"
    for name, data in members:
        assert sha(z.read(name)) == claimed[name] == sha(data), name

    print(f"wrote {OUT.name} — {len(names)} members + MANIFEST, "
          f"{OUT.stat().st_size / 1024:.0f} KB")
    print(f"bundle sha256 {sha(OUT.read_bytes())}")
    print("\nPINNED SOURCE VERIFICATION")
    print("\n".join(pin_lines))
    if failures:
        print(f"\n{len(failures)} pin(s) do not verify: {failures}")
        print("(expected: chunker.py — see the errata block; documented, not silent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
