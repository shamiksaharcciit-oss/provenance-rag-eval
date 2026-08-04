# Merlin embedding service

The Merlin embedding service turns document chunks into 1024-dimensional vectors for the Kestrel indexer. It batches up to 64 chunks per request to keep GPU utilisation above 80 percent.

This service caches embeddings by SHA-256 content hash. Repeated ingestion of an unchanged document therefore costs nothing beyond the hash lookup, which is what makes a full corpus re-scan cheap enough to run nightly.

It runs the bge-large-en-v1.5 model behind a Triton inference server. Swapping the model requires a full reindex, because vectors produced by different models are not comparable and mixing them silently destroys recall.

## Throughput

A single A100 sustains roughly 900 chunks per second at the default batch size. The service scales horizontally behind a round-robin load balancer; there is no shared state between replicas beyond the cache.

It batches up to 64 chunks per request to keep GPU utilisation above 80 percent.

## Failure modes

This service returns HTTP 503 when the GPU queue exceeds 2000 pending chunks. Callers are expected to retry with exponential backoff, and the Harrier query router treats a 503 as a soft failure rather than an error.
