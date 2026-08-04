"""v1.9 §1 — the generator client, the G5 pin, and the G2 determinism probe.

WHY THIS MODULE EXISTS RATHER THAN CALLING `LLMClient` DIRECTLY. Two frozen requirements cannot
be met through the shared client as it stands, and §8 forbids editing anything outside `v19/`:

  * **G5's pin** needs `response.model` logged on every call. `LLMClient._call_anthropic`
    returns `(text, input_tokens, output_tokens)` and discards `msg.model`, so no caller can
    see it.
  * **G2's probe bypass** needs repeats that read nothing and write nothing. `complete()`
    returns early on a cache hit and unconditionally writes the response on a miss, so every
    repeat after the first would be served from disk — the probe would measure the cache, not
    the model. That is the defect G2 ruled on, and it is latent in v1.7's cancelled E2 §3.2.

`V19Client` subclasses `LLMClient` INSIDE `v19/`. Nothing in `src/` is touched, and — this is
the point of subclassing rather than writing a fresh SDK wrapper — **the cost guard still
binds**: `complete_uncached` runs the same `max_llm_calls` / `max_usd` checks before any paid
call. A hand-rolled client would have bypassed the guard silently, which §6 forbids editing and
therefore certainly forbids evading.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from src.llm.client import CostGuardExceeded, LLMClient


class ModelPinViolated(RuntimeError):
    """`response.model` changed mid-run. APPARATUS-STOP per G5."""


class ProbeServedFromCache(RuntimeError):
    """A probe repeat was not a fresh call. The probe would measure the cache, not the model."""


class V19Client(LLMClient):
    """`LLMClient` plus the observable pin and a cache-bypassing path."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.models_seen: list[str] = []
        self.finish_reasons: list[str] = []
        self.output_lengths: list[int] = []
        self.uncached_calls = 0
        self.started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # -- G5: capture what the shared client discards ------------------------
    def _call_anthropic(self, prompt: str, system: str):
        """Same call as the parent; additionally records `response.model` and finish reason.

        Implemented by re-entering the parent and reading the SDK's last response would require
        the parent to keep it, which it does not — so the call is made here, and the parent's
        truncation contract is preserved exactly.
        """
        from src.llm.client import LLMTruncatedError

        if self._client is None:
            import os

            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=key)

        def _create():
            kwargs = dict(model=self.model, max_tokens=self.max_tokens, system=system or "",
                          thinking={"type": "disabled"},
                          messages=[{"role": "user", "content": prompt}])
            if not self._omit_temperature:
                kwargs["temperature"] = self.temperature
            return self._client.messages.create(**kwargs)

        try:
            msg = _create()
        except Exception as e:
            if "temperature" in str(e).lower() and not self._omit_temperature:
                self._omit_temperature = True
                msg = _create()
            else:
                raise

        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        in_tok = getattr(msg.usage, "input_tokens", 0)
        out_tok = getattr(msg.usage, "output_tokens", 0)
        stop = getattr(msg, "stop_reason", None)

        self.models_seen.append(getattr(msg, "model", "<absent>"))
        self.finish_reasons.append(str(stop))          # G6 guard: logged for every call
        self.output_lengths.append(len(text))
        self.assert_model_constant()

        if stop == "max_tokens" or not text.strip():
            raise LLMTruncatedError(
                f"truncated/empty completion (stop_reason={stop!r}, out_tok={out_tok}, "
                f"max_tokens={self.max_tokens}, text_len={len(text)})")
        return text, in_tok, out_tok

    def assert_model_constant(self) -> None:
        distinct = sorted(set(self.models_seen))
        if len(distinct) > 1:
            raise ModelPinViolated(
                f"response.model changed mid-run: {distinct}. APPARATUS-STOP per G5 — the pin "
                f"is the only thing the surface lets us pin, so its violation ends the run.")

    # -- G2: a path that reads nothing and writes nothing --------------------
    def complete_uncached(self, prompt: str, system: str = "") -> str:
        """A guaranteed-fresh call. Never reads the cache, never writes it.

        The cost guard still runs: bypassing the cache must not mean bypassing the budget.
        """
        if self.is_none:
            raise RuntimeError("complete_uncached() called with provider='none'")
        if self.calls + 1 > self.max_llm_calls:
            raise CostGuardExceeded(f"max_llm_calls={self.max_llm_calls} would be exceeded")
        if self.est_usd > self.max_usd:
            raise CostGuardExceeded(f"max_usd={self.max_usd} exceeded (est ${self.est_usd:.2f})")
        text, in_tok, out_tok = self._call_provider(prompt, system)
        self.calls += 1
        self.uncached_calls += 1
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        return text

    def pin_record(self) -> dict:
        """The G5 pin as it will appear in the manifest."""
        return {"requested_model": self.model,
                "response_model_distinct": sorted(set(self.models_seen)),
                "n_calls_observed": len(self.models_seen),
                "run_started_utc": self.started_utc,
                "run_ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "_note": ("G5: the strongest pin the surface offers. A dated snapshot id does "
                          "not exist to be pinned.")}

    def anomaly_record(self) -> dict:
        """G6's guard: finish reasons and output lengths, reported descriptively."""
        from collections import Counter
        return {"finish_reasons": dict(Counter(self.finish_reasons)),
                "output_length_min": min(self.output_lengths, default=None),
                "output_length_max": max(self.output_lengths, default=None),
                "n": len(self.output_lengths)}


def determinism_probe(client: V19Client, prompts: list[str], repeats: int = 3,
                      max_calls: int = 500) -> dict:
    """G2's probe: repeats bypass the cache, and the harness asserts they were fresh.

    Returns the verdict plus per-prompt agreement. Raises `ProbeServedFromCache` if the fresh
    call count does not equal `len(prompts) * repeats` — the probe fails loudly rather than
    reporting determinism it never tested.
    """
    need = len(prompts) * repeats
    if need > max_calls:
        raise RuntimeError(
            f"probe would need {need} calls, over the {max_calls} bound (§1). Reduce the sample "
            f"before the freeze, not during the run.")
    before = client.uncached_calls
    outs: list[list[str]] = []
    for p in prompts:
        outs.append([client.complete_uncached(p) for _ in range(repeats)])
    fresh = client.uncached_calls - before
    if fresh != need:
        raise ProbeServedFromCache(
            f"probe made {fresh} fresh calls, expected {need}. A repeat was served from cache, "
            f"so this probe measured the cache and not the model (G2).")
    identical = [len(set(o)) == 1 for o in outs]
    return {"repeats": repeats, "n_prompts": len(prompts), "fresh_calls": fresh,
            "all_identical": all(identical),
            "n_prompts_identical": sum(identical),
            "verdict": "DETERMINISTIC" if all(identical) else "NONDETERMINISTIC",
            "_note": ("Track A dev only; verdict extends to Track B as a declared "
                      "sampler-property assumption (G6), not as a measurement there.")}


def write_probe_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
