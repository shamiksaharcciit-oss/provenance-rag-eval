"""Cached LLM client (plan §11).

- provider "none": no network, no cost. Callers detect this via `.is_none` and use
  their own deterministic rule-based stubs (clearly labeled). `complete()` raises,
  so a stub path is never silently skipped.
- provider "anthropic": real API at temperature 0, every call cached by a content
  hash of (model, system, prompt). Cost guard aborts if limits are exceeded.

Determinism: same (model, system, prompt) -> identical cached response, so two runs
of the same config produce identical metrics (§3 rule 3, §11 idempotency).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path


class CostGuardExceeded(RuntimeError):
    pass


class LLMTruncatedError(RuntimeError):
    """Raised when a completion is truncated (stop_reason=max_tokens) or empty.

    Such a response must never be cached or silently accepted as a formatter
    result — doing so let a rule-based fallback masquerade as a real treatment
    (the stamps_total=0 bug that invalidated the first v1.2 run).
    """
    pass


# Rough per-model USD/token estimate for the cost guard only (not billing-accurate).
_USD_PER_INPUT_TOKEN = 5.0 / 1_000_000
_USD_PER_OUTPUT_TOKEN = 25.0 / 1_000_000


@dataclass
class LLMClient:
    provider: str = "none"
    model: str = "claude-opus-4-8"
    temperature: float = 0.0
    max_tokens: int = 1024
    cache_dir: Path = field(default_factory=lambda: Path("cache/llm"))
    max_llm_calls: int = 100_000
    max_usd: float = 25.0

    # live counters (recorded into results.json cost block, §7.7)
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0
    cached_input_tokens: int = 0
    cached_output_tokens: int = 0
    _client: object | None = None
    _omit_temperature: bool = False  # some models (e.g. opus-4-8) deprecate temperature

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- introspection ------------------------------------------------------
    @property
    def is_none(self) -> bool:
        return self.provider == "none"

    @property
    def est_usd(self) -> float:
        return (self.input_tokens * _USD_PER_INPUT_TOKEN
                + self.output_tokens * _USD_PER_OUTPUT_TOKEN)

    # -- caching ------------------------------------------------------------
    def _cache_key(self, system: str, prompt: str) -> str:
        h = hashlib.sha256()
        h.update(self.model.encode())
        h.update(b"\x00")
        h.update((system or "").encode())
        h.update(b"\x00")
        h.update(prompt.encode())
        h.update(f"\x00t={self.temperature}\x00m={self.max_tokens}".encode())
        return h.hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    # -- main entrypoint ----------------------------------------------------
    def complete(self, prompt: str, system: str = "") -> str:
        """Return model text for `prompt`. Cached; cost-guarded.

        Raises if provider == 'none' (callers must branch on `.is_none` first).
        """
        if self.is_none:
            raise RuntimeError(
                "LLMClient.complete() called with provider='none'. "
                "Callers must branch on `.is_none` and use a rule-based stub."
            )

        key = self._cache_key(system, prompt)
        cpath = self._cache_path(key)
        if cpath.exists():
            self.cache_hits += 1
            rec = json.loads(cpath.read_text(encoding="utf-8"))
            self.cached_input_tokens += rec.get("input_tokens", 0)
            self.cached_output_tokens += rec.get("output_tokens", 0)
            return rec["text"]

        # Cost guard (§11) — check BEFORE making the paid call.
        if self.calls + 1 > self.max_llm_calls:
            raise CostGuardExceeded(
                f"max_llm_calls={self.max_llm_calls} would be exceeded")
        if self.est_usd > self.max_usd:
            raise CostGuardExceeded(
                f"max_usd={self.max_usd} exceeded (est ${self.est_usd:.2f})")

        text, in_tok, out_tok = self._call_provider(prompt, system)

        self.calls += 1
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        cpath.write_text(
            json.dumps({"text": text, "input_tokens": in_tok, "output_tokens": out_tok,
                        "model": self.model}, ensure_ascii=False),
            encoding="utf-8",
        )
        return text

    def _call_provider(self, prompt: str, system: str) -> tuple[str, int, int]:
        if self.provider == "anthropic":
            return self._call_anthropic(prompt, system)
        raise ValueError(f"unknown llm provider {self.provider!r}")

    def _call_anthropic(self, prompt: str, system: str) -> tuple[str, int, int]:
        if self._client is None:
            try:
                import anthropic  # lazy import
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "anthropic SDK not installed; `pip install anthropic` or use provider=none"
                ) from e
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=api_key)

        def _create():
            # Thinking is ON by default on Sonnet-5 (adaptive) and consumes the
            # shared max_tokens budget before any text is emitted; on long docs
            # it exhausts the budget and returns stop_reason=max_tokens with an
            # empty text block. This is a deterministic structured-JSON extraction,
            # so disable thinking to give the whole budget to the answer. Opus-4-8
            # runs without thinking when omitted, so this is a no-op there and does
            # NOT change the cache key (thinking is not part of the key) -> cached
            # Track A results remain valid.
            kwargs = dict(model=self.model, max_tokens=self.max_tokens,
                          system=system or "",
                          thinking={"type": "disabled"},
                          messages=[{"role": "user", "content": prompt}])
            if not self._omit_temperature:
                kwargs["temperature"] = self.temperature
            return self._client.messages.create(**kwargs)  # type: ignore[attr-defined]

        try:
            msg = _create()
        except Exception as e:  # newer models deprecate temperature -> retry without it
            if "temperature" in str(e).lower() and not self._omit_temperature:
                self._omit_temperature = True
                msg = _create()
            else:
                raise
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        in_tok = getattr(msg.usage, "input_tokens", 0)
        out_tok = getattr(msg.usage, "output_tokens", 0)
        stop = getattr(msg, "stop_reason", None)
        # Fail LOUD on a truncated/empty completion. A formatter that returns
        # partial or empty JSON must not be silently accepted (and — see
        # complete() — must never be cached), or a rule-based fallback would
        # masquerade as a valid treatment result. This is what invalidated the
        # first v1.2 run: stamps_total=0 because the treatment never executed.
        if stop == "max_tokens" or not text.strip():
            raise LLMTruncatedError(
                f"truncated/empty completion (stop_reason={stop!r}, "
                f"out_tok={out_tok}, max_tokens={self.max_tokens}, text_len={len(text)})"
            )
        return text, in_tok, out_tok

    def snapshot(self) -> dict:
        """Current counters, for per-condition cost attribution (v1.1 §5.3)."""
        return {"fresh_calls": self.calls, "cached_calls": self.cache_hits,
                "fresh_tokens": self.input_tokens + self.output_tokens,
                "cached_tokens": self.cached_input_tokens + self.cached_output_tokens}

    @staticmethod
    def delta(before: dict, after: dict) -> dict:
        return {k: after[k] - before[k] for k in before}

    def cost_summary(self) -> dict:
        return {
            "llm_calls": self.calls,
            "llm_tokens": self.input_tokens + self.output_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_hits": self.cache_hits,
            "est_usd": round(self.est_usd, 4),
        }


def build_llm(cfg: dict) -> LLMClient:
    lc = cfg.get("llm", {})
    guard = cfg.get("cost_guard", {})
    return LLMClient(
        provider=lc.get("provider", "none"),
        model=lc.get("model", "claude-opus-4-8"),
        temperature=lc.get("temperature", 0.0),
        max_tokens=lc.get("max_tokens", 1024),
        cache_dir=Path(cfg.get("_cache_root", "cache")) / "llm",
        max_llm_calls=guard.get("max_llm_calls", 100_000),
        max_usd=guard.get("max_usd", 25.0),
    )
