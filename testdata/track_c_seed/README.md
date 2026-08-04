# Track C / M5 seed corpus — the Raptor platform

Five pages of fictional named-system documentation, written to exercise the semantic
formatter rather than to read well. They serve two purposes:

1. **Forge M5 cross-check (§7.5)** — paste into a Confluence space, then run
   `npm run crosscheck -- <the 5 page ids>`. The stock Atlassian template spaces produced
   zero reference-resolution edits and left the diff gate untested; this corpus is built
   to fire both.
2. **Track C** — `src/datasets/track_c_internal.py` reads a directory of `.md` files plus
   `queries.jsonl`. Copy these to `data/internal/` and author human-verified gold spans
   alongside them. Track C is revisit condition #3 for identity injection.

## Why each page is shaped the way it is

Every page was written against a specific requirement of the pass:

| Requirement | How it is met | Fires |
|---|---|---|
| Clean named subject | H1 is a bare system name, so `subjectPhrase` returns e.g. "The Kestrel indexer" rather than a banner fragment | prerequisite for everything |
| Dangling references | Paragraphs open with "It", "This service", "This tool", "This router" | reference resolution |
| Genuine restatement | One sentence per page is repeated **verbatim** in a later section | de-duplication |
| Protected tokens in edited sentences | Ports (50051, 9102), versions (bge-large-en-v1.5), identifiers (HNSW, M=32, KESTREL_GRPC_PORT), quantities (400 days, 250 ms) sit inside the sentences most likely to be reference-resolved | **the diff gate** |

That last row is the point. The guardrail only runs on reference-resolution edits, so a
corpus with no such edits leaves the safety-critical half of the formatter unverified — which
is exactly what happened on the template spaces.

## Cross-document structure

The five components reference each other (Falconry checks Osprey; Harrier fans out to
Kestrel; Kestrel consumes Merlin). That is deliberate: it gives Track C multi-hop queries
whose answers span documents, and it gives the formatter genuine cross-references to resolve.

## Pasting into Confluence

Create one page per file. **Title the page exactly as the H1** — Confluence stores the title
separately from the body, and the body's H1 is what `subjectPhrase` reads. Pasting the
markdown into the editor converts it to ADF automatically.

Then confirm the corpus looks right before spending LLM calls:

```powershell
npm run crosscheck -- --inspect <id1> <id2> <id3> <id4> <id5>
```

Every page should report several multi-sentence paragraphs. Compare against the template
pages, which reported zero prose words.

## These facts are invented

Nothing here describes a real system. That is fine for measuring the formatter — it needs
prose with a named subject, back-references and protected tokens, not true facts. It matters
for Track C only in that the gold spans must be verified against *these documents*, which is
what `scripts/build_gold.py` drafts and a human confirms.
