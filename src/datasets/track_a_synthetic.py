"""Track A — controlled synthetic corpus (plan §5.1-A).

Builds clean seed "documents" about fictional technical systems, then programmatically
DEGRADES them to simulate messy corpora, recording gold spans BY CONSTRUCTION:

  * anaphora        -> replace the subject entity in a later sentence with a pronoun,
                       leaving the definition earlier (context-starvation).
  * duplication     -> restate a fact in 2-3 scattered places.
  * definition/usage split -> push facts far from the intro with intervening filler
                       (boundary-misalignment pressure).

Gold spans are exact char offsets into the FINAL (degraded) document text, which is
what every condition indexes. Fully reproducible from `seed`. Zero network, zero LLM.
"""
from __future__ import annotations

import random

from src.datasets.base import Dataset, Document, GoldSpan, Query
from src.textutil import count_tokens

# --- vocabulary pools (deterministic sampling) ------------------------------
_ADJ = ["Kestrel", "Basalt", "Cobalt", "Ember", "Cirrus", "Onyx", "Halcyon",
        "Vega", "Quartz", "Zephyr", "Marlin", "Falcon", "Ridge", "Solstice",
        "Aster", "Beacon", "Nimbus", "Talon", "Verde", "Crag", "Drift", "Fable",
        "Glint", "Harbor", "Ion", "Juniper", "Krait", "Lattice", "Mica", "Nyx"]
_NOUN = ["indexer", "cache", "router", "scheduler", "gateway", "planner",
         "compactor", "broker", "resolver", "ledger", "collator", "sharder"]

# Each attribute: (key, sentence template using {SUBJ} and {V}, value pool, question)
# Values include verbatim identifiers/terms/numbers -> stress the H2 guardrail.
_ATTRS = [
    ("algorithm",
     "{SUBJ} uses the {V} algorithm for approximate nearest-neighbor search.",
     ["HNSW", "IVF-PQ", "ScaNN", "DiskANN", "NGT", "Annoy"],
     "Which algorithm does {ENT} use for approximate nearest-neighbor search?"),
    ("timeout",
     "{SUBJ} applies a default request timeout of {V} milliseconds.",
     ["350", "500", "1200", "750", "250", "900"],
     "What is the default request timeout of {ENT} in milliseconds?"),
    ("format",
     "{SUBJ} persists its index to disk in the {V} file format.",
     ["Parquet", "Arrow", "ORC", "Avro", "Lance", "Protobuf"],
     "In which file format does {ENT} persist its index to disk?"),
    ("version",
     "{SUBJ} reached general availability in release {V}.",
     ["v2.3.1", "v4.0.0", "v1.7.2", "v3.5.0", "v5.1.4", "v0.9.8"],
     "In which release did {ENT} reach general availability?"),
    ("throughput",
     "{SUBJ} sustains up to {V} queries per second on a single node.",
     ["18000", "42000", "9500", "125000", "3300", "67000"],
     "How many queries per second can {ENT} sustain on a single node?"),
    ("port",
     "{SUBJ} listens for gRPC traffic on port {V} by default.",
     ["50051", "8443", "9090", "7000", "6565", "8081"],
     "On which port does {ENT} listen for gRPC traffic by default?"),
    ("cache_policy",
     "{SUBJ} evicts hot vectors using a {V} replacement policy.",
     ["LRU", "LFU", "ARC", "2Q", "CLOCK-Pro", "S3-FIFO"],
     "Which replacement policy does {ENT} use to evict hot vectors?"),
    ("license",
     "{SUBJ} is distributed under the {V} license.",
     ["Apache-2.0", "BSD-3-Clause", "MIT", "MPL-2.0", "GPL-3.0", "AGPL-3.0"],
     "Under which license is {ENT} distributed?"),
]

_PRONOUNS = ["It", "This system", "The system", "This component"]

# Filler must be UNIQUE within a document, otherwise the formatter's de-duplication
# would collapse a repeated-sentence document down to almost nothing and inflate recall
# for the wrong reason (an artifact, not reference-resolution). We therefore generate
# filler combinatorially (12*10*10*10 = 12000 distinct sentences) and sample WITHOUT
# replacement per document. None of this vocabulary collides with query terms, entity
# names, or answer values, so filler never accidentally overlaps a gold span.
_F_SUBJ = ["deployment pipeline", "operations runbook", "observability layer",
           "access controller", "migration tool", "scheduler daemon", "backup service",
           "audit trail", "health monitor", "configuration loader", "release manager",
           "rollout coordinator"]
_F_VERB = ["documents", "validates", "coordinates", "reconciles", "rotates", "audits",
           "provisions", "throttles", "replicates", "checkpoints"]
_F_OBJ = ["rolling upgrades", "readiness probes", "archive rotation", "topology changes",
          "scoped credentials", "seasonal demand", "retry budgets", "canary cohorts",
          "rollout gates", "incident triage"]
_F_TAIL = ["without downtime", "across availability zones", "on a fixed cadence",
           "behind a standard proxy", "under peak demand", "during maintenance windows",
           "with backward compatibility", "per environment", "using warm standbys",
           "for compliance reviews"]


def _unique_filler(rng: random.Random, n: int) -> list[str]:
    """Return n distinct filler sentences (unique within a document)."""
    out: list[str] = []
    seen: set[str] = set()
    guard = 0
    while len(out) < n and guard < n * 50:
        guard += 1
        s = ("The %s %s %s %s." % (rng.choice(_F_SUBJ), rng.choice(_F_VERB),
                                   rng.choice(_F_OBJ), rng.choice(_F_TAIL)))
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _pick(rng: random.Random, pool: list[str], k: int) -> list[str]:
    return rng.sample(pool, k)


class _DocBuilder:
    """Assembles paragraphs while recording exact char spans of fact sentences."""

    def __init__(self) -> None:
        self.text = ""
        self.spans: dict[str, tuple[int, int]] = {}

    def add_paragraph(self, sentences: list[tuple[str, str | None]]) -> None:
        if self.text:
            self.text += "\n\n"
        local = ""
        base = len(self.text)
        for i, (s, key) in enumerate(sentences):
            if local:
                local += " "
            start = base + len(local)
            local += s
            end = base + len(local)
            if key is not None:
                # record; for duplicated facts keep the FIRST occurrence's key and
                # add numbered keys for the rest.
                self.spans[key] = (start, end)
        self.text += local


def _make_document(rng: random.Random, idx: int, cfg: dict) -> tuple[Document, list[dict]]:
    adj = _ADJ[idx % len(_ADJ)]
    noun = _NOUN[(idx // len(_ADJ) + idx) % len(_NOUN)]
    entity = f"{adj} {noun}"           # e.g. "Kestrel indexer"
    subj = f"The {entity}"             # sentence subject
    doc_id = f"A-{idx:03d}-{adj.lower()}-{noun}"

    n_facts = rng.randint(5, min(8, len(_ATTRS)))
    attrs = rng.sample(_ATTRS, n_facts)

    # Choose one distinct value per attribute for THIS doc.
    facts = []  # each: {key, attr_key, value, sentence, question_template, degraded, dup}
    for (akey, templ, pool, q) in attrs:
        value = rng.choice(pool)
        facts.append({
            "key": akey, "template": templ, "value": value, "question": q,
            "sentence_subj": templ.format(SUBJ=subj, V=value),
            "sentence_pron": None, "degraded": False,
        })

    anaphora_rate = cfg.get("anaphora_rate", 0.5)
    dup_copies = cfg.get("duplication_copies", 2)

    b = _DocBuilder()
    # Title + definition/intro paragraph (names the entity — the referent).
    b.add_paragraph([(f"# {entity}", None)])
    intro = (f"{subj} is a distributed vector-search {noun} used in production "
             f"retrieval systems.")
    b.add_paragraph([(intro, None)])

    # Per-document unique filler supply, drawn without replacement so de-duplication
    # never collapses the document (the artifact that inflated recall in an earlier run).
    _pool = _unique_filler(rng, 700)
    _pi = [0]

    def next_filler() -> str:
        if _pi[0] >= len(_pool):
            _pool.extend(_unique_filler(rng, 400))
        s = _pool[_pi[0]]
        _pi[0] += 1
        return s

    fact_records: list[dict] = []

    # Emit facts, interleaving substantial filler to push facts far from the intro
    # (definition/usage split) so documents span MANY chunks and facts are distributed
    # well beyond the largest swept chunk size (768 tokens). This guarantees that a
    # degraded fact lands in a chunk that does NOT contain the entity definition, so
    # even a well-tuned naive baseline suffers context-starvation. Degrade
    # ~anaphora_rate of the fact sentences with a pronoun (context-starvation).
    for fi, fact in enumerate(facts):
        n_fill = rng.randint(10, 16)
        for _ in range(n_fill):
            b.add_paragraph([(next_filler(), None)])

        degrade = rng.random() < anaphora_rate
        if degrade:
            pron = rng.choice(_PRONOUNS)
            sent = fact["template"].format(SUBJ=pron, V=fact["value"])
            fact["degraded"] = True
        else:
            sent = fact["sentence_subj"]

        key = f"fact::{fact['key']}"
        b.add_paragraph([(sent, key)])
        gold_ranges = [b.spans[key]]

        # Duplication: restate the fact in scattered later paragraphs.
        n_dup = rng.randint(0, 1) * (dup_copies - 1)  # 0 or (copies-1) extra copies
        for d in range(n_dup):
            # separate the copies with filler
            b.add_paragraph([(next_filler(), None)])
            restated = f"To recap, {sent[0].lower()}{sent[1:]}"
            dkey = f"{key}::dup{d}"
            b.add_paragraph([(restated, dkey)])
            gold_ranges.append(b.spans[dkey])

        fact_records.append({**fact, "entity": entity, "gold_ranges": gold_ranges})

    # Tail filler + a length floor so the whole document cannot fit in one chunk even at
    # the largest swept chunk size (min_doc_tokens > 768). Keeps the definition/usage
    # split meaningful for every baseline.
    for _ in range(rng.randint(8, 14)):
        b.add_paragraph([(next_filler(), None)])
    min_doc_tokens = cfg.get("min_doc_tokens", 1100)
    guard = 0
    while count_tokens(b.text) < min_doc_tokens and guard < 400:
        b.add_paragraph([(next_filler(), None)])
        guard += 1

    doc = Document(doc_id=doc_id, text=b.text)
    return doc, fact_records


def _build_queries(rng: random.Random, doc: Document, facts: list[dict]) -> list[Query]:
    queries: list[Query] = []
    ent = facts[0]["entity"] if facts else "the system"

    # Factual: one per fact.
    for fi, f in enumerate(facts):
        gold = [GoldSpan(doc.doc_id, s, e) for (s, e) in f["gold_ranges"]]
        qid = f"{doc.doc_id}::f{fi}"
        queries.append(Query(
            query_id=qid,
            text=f["question"].format(ENT=f"the {f['entity']}"),
            gold_spans=gold,
            answer=f["value"],
            qtype="factual",
        ))

    # Multi-hop: identify the system by attribute B, ask attribute A (same doc).
    if len(facts) >= 2:
        a, bfact = rng.sample(facts, 2)
        gold = [GoldSpan(doc.doc_id, s, e) for (s, e) in a["gold_ranges"]]
        q = (f"For the vector-search system whose {bfact['key'].replace('_', ' ')} "
             f"is {bfact['value']}, {a['question'].format(ENT='it').rstrip('?')}?")
        queries.append(Query(
            query_id=f"{doc.doc_id}::mh",
            text=q, gold_spans=gold, answer=a["value"], qtype="multi_hop",
        ))

    # Synthesis: summarize several defaults; gold = several fact sentences.
    if len(facts) >= 3:
        chosen = facts[:3]
        gold = []
        for f in chosen:
            gold.extend(GoldSpan(doc.doc_id, s, e) for (s, e) in f["gold_ranges"])
        ans = "; ".join(f"{f['key']}={f['value']}" for f in chosen)
        queries.append(Query(
            query_id=f"{doc.doc_id}::syn",
            text=f"Summarize the key configuration defaults of the {ent}.",
            gold_spans=gold, answer=ans, qtype="synthesis",
        ))
    return queries


def load(cfg: dict, seed: int) -> Dataset:
    """Generate the Track A dataset deterministically from `seed`."""
    params = cfg.get("params", cfg)
    n_docs = params.get("n_docs", 45)
    n_queries = params.get("n_queries", 220)
    rng = random.Random(seed)

    documents: list[Document] = []
    all_queries: list[Query] = []
    for i in range(n_docs):
        # per-doc RNG derived from global seed for stability regardless of n_docs
        drng = random.Random(seed * 100003 + i)
        doc, facts = _make_document(drng, i, params)
        documents.append(doc)
        all_queries.extend(_build_queries(drng, doc, facts))

    # Deterministically sample down to n_queries, keeping a qtype mix.
    rng.shuffle(all_queries)
    if len(all_queries) > n_queries:
        by_type: dict[str, list[Query]] = {"factual": [], "multi_hop": [], "synthesis": []}
        for q in all_queries:
            by_type[q.qtype].append(q)
        # keep all multi_hop + synthesis, fill remainder with factual
        keep = by_type["multi_hop"] + by_type["synthesis"]
        remainder = n_queries - len(keep)
        keep = keep + by_type["factual"][:max(0, remainder)]
        rng.shuffle(keep)
        all_queries = keep[:n_queries]

    meta = {"track": "A", "n_docs": len(documents), "seed": seed,
            "note": "synthetic; gold by construction; zero LLM/network"}
    return Dataset(track_id="A", documents=documents, queries=all_queries, meta=meta)
