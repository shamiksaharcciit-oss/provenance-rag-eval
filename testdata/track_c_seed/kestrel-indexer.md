# Kestrel indexer

The Kestrel indexer is the vector-search component of the Raptor platform. It builds and serves approximate-nearest-neighbour indexes over embedded document chunks produced by the Merlin embedding service.

It listens for gRPC traffic on port 50051 by default. Operators can override that with the KESTREL_GRPC_PORT environment variable, though the health endpoint stays on port 8080 regardless of how the service is configured.

The indexer uses HNSW graphs with M=32 and efConstruction=200. These parameters were chosen after benchmarking against ScaNN on the 2.4M-chunk internal corpus, where HNSW held a 4-point recall advantage at equal latency.

## Sharding

Each index is split into 16 shards by document hash. A shard holds at most 200k vectors; the indexer refuses writes beyond that ceiling rather than silently degrading recall.

It listens for gRPC traffic on port 50051 by default.

## Recovery

This system rebuilds a corrupted shard from the write-ahead log in under 90 seconds. It does not replicate shards across availability zones — that responsibility sits with the Falconry deployment runbook, which staggers rollouts so a single zone failure never takes every replica at once.
