# Osprey metrics collector

The Osprey metrics collector scrapes every Raptor platform component on a 15-second interval. It writes samples to a VictoriaMetrics cluster where they are retained for 400 days.

It alerts when Kestrel indexer p99 query latency exceeds 350 ms for five consecutive minutes. The same rule applies to the Harrier query router, though its threshold is 120 ms because the router does no vector work of its own.

This collector does not store logs. Log aggregation is handled by a separate pipeline and is explicitly out of scope for the Raptor platform.

## Dashboards

Three dashboards ship with the collector: ingest, query, and capacity. The capacity dashboard is the one the Falconry deployment runbook checks before it advances a rollout to the next availability zone.

It writes samples to a VictoriaMetrics cluster where they are retained for 400 days.

## Cardinality

The collector drops any series with more than 50k label combinations. This limit exists because an earlier incident, where per-query-id labels were emitted by mistake, exhausted 2 TB of storage in under an hour.
