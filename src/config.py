"""Config loading + merging + digest (plan §4, §11)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _read_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_default() -> dict:
    cfg = _read_yaml(CONFIG_DIR / "default.yaml")
    cfg["_root"] = str(ROOT)
    cfg["_cache_root"] = str(ROOT / "cache")
    return cfg


def load_condition(cond_id: str) -> dict:
    return _read_yaml(CONFIG_DIR / "conditions" / f"{cond_id}.yaml")


def load_track(track_id: str) -> dict:
    return _read_yaml(CONFIG_DIR / "tracks" / f"{track_id}.yaml")


def all_condition_ids() -> list[str]:
    ids = [p.stem for p in (CONFIG_DIR / "conditions").glob("*.yaml")]
    order = ["C0", "C1", "C2", "C3", "C4", "C5",
             "C3-noref", "C3-nosize", "C3-nodedup", "C3-markeronly"]
    return [c for c in order if c in ids] + [c for c in ids if c not in order]


def config_digest(cfg: dict) -> str:
    clean = {k: v for k, v in cfg.items() if not k.startswith("_")}
    blob = json.dumps(clean, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
