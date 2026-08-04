# Falconry deployment runbook

The Falconry deployment runbook describes how Raptor platform components are released. It rolls out new versions one availability zone at a time, never touching two zones concurrently.

It waits for the health endpoint to return HTTP 200 for 60 consecutive seconds before advancing to the next zone. A failed check rolls that zone back to the previous image tag automatically, without operator involvement.

This tool refuses to deploy while the Osprey metrics collector reports an open sev-1 alert. Operators can override the block with the --force flag, which is written to the audit log and requires a matching change ticket.

## Order of operations

Components are released bottom-up: the Merlin embedding service first, then the Kestrel indexer, then the Harrier query router. Releasing the router before the indexer is the one ordering that will break a live cluster, because the router assumes shard APIs that older indexer builds do not expose.

It rolls out new versions one availability zone at a time, never touching two zones concurrently.

## Rollback

A full rollback across all 3 zones takes about 12 minutes. The runbook does not roll back schema migrations, so any release containing one must be reverted by hand.
