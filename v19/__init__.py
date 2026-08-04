"""v1.9 READING-RESIDUAL — the reading test under its own freeze.

Measures the one mechanism v1.7 left alive: given the same information, in same-sized parcels,
with equal structural delivery, does the formatter's repaired prose change what a generator
extracts from it?

Nothing in this package calls a model at import time. `v19.generate` is the only module that can
issue a call, and it refuses to until it is handed an explicit budget.
"""
