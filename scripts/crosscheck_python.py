"""CLI cross-check, Python side (Forge spec §7.5).

Reads the artifacts written by `forge-app/scripts/crosscheck.ts` and runs the SAME blocks
through the Python package's prompt construction, JSON parser and diff gate — the code that
produced the published evaluation.

Default mode is REPLAY: the model response the TS side already paid for is fed to the Python
parser, so the comparison is deterministic and free. That separates the two questions §7.5
conflates:

  * did the two IMPLEMENTATIONS drift?      -> replay mode answers this exactly, every run
  * does the MODEL answer the same twice?   -> `--live` measures it, and it is noise, not drift

`--live` issues the Python side's own call (through the real LLMClient, so it is cached and
cost-guarded like any eval run) and records both answers.

Usage:
    python scripts/crosscheck_python.py            # replay (free, deterministic)
    python scripts/crosscheck_python.py --live     # also re-query the model
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.chunkers.formatter import (  # noqa: E402
    _parse_formatter_json,
    _subject_phrase,
    diff_gate_ok,
)
from src.chunkers.prompts import (  # noqa: E402
    PROMPTS_VERSION,
    formatter_system_prompt,
    formatter_user_prompt,
    number_sentences,
)

CROSSCHECK = REPO / "crosscheck"

if hasattr(sys.stdout, "reconfigure"):  # Windows console defaults to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def block_spans(texts: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """Join blocks into one document and return each block's span.

    This is the deliberate substitution at the heart of the cross-check: the CLI normally
    derives spans with `sentence_spans`, which splits prose into sentences. Here each ADF
    block is treated as one unit, so both sides see identical input and any difference in
    the output is attributable to the formatter code, not to segmentation.
    """
    doc, spans, cursor = [], [], 0
    for t in texts:
        spans.append((cursor, cursor + len(t)))
        doc.append(t)
        cursor += len(t) + 2  # the "\n\n" joiner
    return "\n\n".join(doc), spans


def run_python_side(blocks: list[dict], raw: str) -> dict:
    """Prompts + parse + gate exactly as `FormatterChunker._chunk_llm` does them."""
    texts = [b["text"] for b in blocks]
    doc_text, spans = block_spans(texts)
    subject = _subject_phrase(doc_text, spans)

    system = formatter_system_prompt(True, True)  # do_ref, do_dedup (v1.1 pass, no identity)
    prompt = formatter_user_prompt(subject, number_sentences(texts))
    data = _parse_formatter_json(raw)

    resolved, dropped = [], []
    if subject:
        for r in data.get("resolved", []):
            i = r.get("i")
            if not (isinstance(i, int) and 0 <= i < len(texts)):
                continue
            original = texts[i]
            # The CLI skips markdown-heading sentences; ADF headings arrive as ordinary
            # blocks, so record the skip rather than hiding it.
            heading_skip = original.startswith("#")
            edited = r.get("text", original)
            resolved.append({
                "i": i,
                "original": original,
                "proposed": edited,
                "gate_ok": bool(diff_gate_ok(original, edited)),
                "heading_skip": heading_skip,
                "applied": bool(diff_gate_ok(original, edited)) and not heading_skip,
            })
    for i in data.get("drop", []):
        if isinstance(i, int) and 0 <= i < len(texts):
            dropped.append({"i": i, "original": texts[i]})

    return {
        "promptsVersion": PROMPTS_VERSION,
        "subject": subject,
        "system": system,
        "prompt": prompt,
        "parsed": {"resolved": data.get("resolved", []), "drop": data.get("drop", [])},
        "resolved": resolved,
        "drop": dropped,
    }


def live_call(system: str, prompt: str, model: str) -> str:
    """The Python side's own model call, through the real cached/cost-guarded client."""
    from src.llm.client import LLMClient

    client = LLMClient(
        provider="anthropic",
        model=model,
        temperature=0.0,
        max_tokens=1024,
        cache_dir=REPO / "cache" / "llm",
    )
    return client.complete(prompt, system=system)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="also issue the Python side's own model call (costs tokens)")
    args = ap.parse_args()

    blocks_dir = CROSSCHECK / "blocks"
    if not blocks_dir.is_dir():
        print("No crosscheck/blocks — run the TS side first:\n"
              "  cd forge-app; npm run crosscheck -- <pageId> ...", file=sys.stderr)
        return 2

    out_dir = CROSSCHECK / "py"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for blocks_file in sorted(blocks_dir.glob("*.json")):
        meta = json.loads(blocks_file.read_text(encoding="utf-8"))
        page_id, blocks = meta["pageId"], meta.get("blocks", [])
        if not blocks:
            print(f"  {page_id} — no blocks, skipped")
            continue

        raw_path = CROSSCHECK / "raw" / f"{page_id}.txt"
        if not raw_path.is_file():
            print(f"  {page_id} — missing raw response, skipped", file=sys.stderr)
            continue
        raw = raw_path.read_text(encoding="utf-8")

        result = run_python_side(blocks, raw)
        result["pageId"] = page_id
        result["title"] = meta.get("title", page_id)
        result["model"] = meta.get("model")
        result["mode"] = "replay"

        if args.live:
            model = meta.get("model") or os.environ.get("CROSSCHECK_MODEL", "claude-sonnet-5")
            own_raw = live_call(result["system"], result["prompt"], model)
            result["mode"] = "live"
            result["own_raw"] = own_raw
            result["own_parsed"] = _parse_formatter_json(own_raw)

        (out_dir / f"{page_id}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {page_id} — {len(result['resolved'])} resolved, {len(result['drop'])} drop")
        count += 1

    print(f"\nwrote {count} page(s) to {out_dir}")
    print("next: python scripts/crosscheck_compare.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
