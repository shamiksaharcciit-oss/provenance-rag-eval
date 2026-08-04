"""Track dispatcher: track config -> canonical Dataset (plan §5.1)."""
from __future__ import annotations

from src.datasets.base import Dataset


def load_track_dataset(track_cfg: dict, seed: int) -> Dataset:
    adapter = track_cfg.get("adapter")
    if adapter == "track_a_synthetic":
        from src.datasets import track_a_synthetic
        return track_a_synthetic.load(track_cfg, seed)
    if adapter == "track_b_public":
        from src.datasets import track_b_public
        return track_b_public.load(track_cfg, seed)
    if adapter == "track_c_internal":
        from src.datasets import track_c_internal
        return track_c_internal.load(track_cfg, seed)
    raise ValueError(f"unknown track adapter {adapter!r}")
