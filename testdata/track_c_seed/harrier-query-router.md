# Harrier query router

The Harrier query router accepts search requests and fans them out to Kestrel indexer shards. It merges the per-shard results using reciprocal rank fusion before returning a single ranked list to the caller.

It applies a 250 ms timeout per shard. Requests that exceed that budget are dropped from the merge rather than failing the whole query, so one slow shard degrades recall instead of causing an outage.

This router rewrites incoming queries before dispatch. It strips stop words, lowercases the text, and expands any acronym listed in the shared synonyms.yaml file maintained alongside the service.

## Observability

Harrier exposes Prometheus metrics on port 9102. The router does not authenticate callers, so the Osprey metrics collector scrapes it over the internal network only.

It merges the per-shard results using reciprocal rank fusion before returning a single ranked list to the caller.

## Limits

The router caps a single request at 64 candidate documents. Raising that cap requires a corresponding increase to the Merlin embedding service batch size, or the added candidates will queue behind embedding work and blow the 250 ms budget.
