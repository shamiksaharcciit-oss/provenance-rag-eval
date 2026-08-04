"""v1.8 — `V18Client`: the observable pin, true payload records, and no sampling parameters.

Ported from v1.9's `V19Client` per the Gate 0(b) §2 ruling. The pattern is a subclass inside the
experiment's own directory that overrides the provider call — **specifically so the shared cost
guard still binds**. Bypassing `src/llm/client.py` entirely would have meant bypassing the
budget, and editing it was not authorised (§10 permits exactly one edit outside `v18/`, the
guard's `max_usd`).

Three defects from Gate 0 are closed here, each by construction rather than by discipline:

* **G10 — the pin that confirmed itself.** `LLMClient._call_anthropic` returns
  `(text, in_tok, out_tok)` and discards `msg.model`; its cache record stores the *requested* id.
  Reading that back proves nothing. `V18Client` captures `response.model` per call and asserts
  it constant, so PF-5's pin applies as written.
* **G9 — a parameter that was never sent.** The pinned model rejects `temperature`
  (`400 ... deprecated for this model`). The parent sends it and silently retries without it on
  the 400, then caches a record saying `t=0.0` for a call that never carried it. Here the
  parameter is **never constructed**, and `build_payload` is the single place a v18 request
  comes into existence — so the manifest describes calls that happened.
* **G11 — a model resolved by default.** `assert_configured_model` refuses to run against
  anything but the id v18 named. Config fall-through is how the probe burned 254 calls
  measuring `claude-opus-4-8`; no v18 call resolves its model by default again.

`build_payload` is deliberately the *only* request constructor, used by both the real-time path
and the Batch API path (`batch.py`). PF-12 requires the batch input to carry true payloads; that
is true by construction because there is one construction.
"""
from __future__ import annotations

import hashlib
import json
import time

from src.llm.client import CostGuardExceeded, LLMClient, LLMTruncatedError


class ModelPinViolated(AssertionError):
    """`response.model` changed mid-run. APPARATUS-STOP per PF-5."""


class ModelNotAsConfigured(AssertionError):
    """A call was about to run against a model v18 did not name. See G11."""


#: §2/§3 — generation and judging. Never inherited from the harness default (G11).
V18_CALL_MODEL = "claude-sonnet-5"


class V18Client(LLMClient):
    """`LLMClient` plus the observable pin, true payload records, and no sampling parameters."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.models_seen: list[str] = []
        self.finish_reasons: list[str] = []
        self.output_lengths: list[int] = []
        self.payload_records: list[dict] = []
        self.started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ------------------------------------------------------------------ the one constructor

    def build_payload(self, prompt: str, system: str = "") -> dict:
        """The single place a v18 request is built. Real-time and batch both call this.

        No `temperature`, no `top_p`, no `top_k` — PF-9: the pinned model accepts none of them,
        and a parameter that cannot be sent must not be constructed, recorded, or implied.
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system or "",
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}],
        }

    @staticmethod
    def payload_digest(payload: dict) -> str:
        """Stable digest of a request. `sort_keys` so the hash cannot drift on dict order."""
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    # ------------------------------------------------------------------------- the pin

    def assert_configured_model(self, expected: str = V18_CALL_MODEL) -> None:
        if self.model != expected:
            raise ModelNotAsConfigured(
                f"client is configured for {self.model!r}, not {expected!r}. A v18 call must "
                f"never resolve its model from a harness default (G11).")

    def assert_model_constant(self) -> None:
        distinct = sorted(set(self.models_seen))
        if len(distinct) > 1:
            raise ModelPinViolated(
                f"response.model changed mid-run: {distinct}. APPARATUS-STOP per PF-5 — the "
                f"served id is the only pin this surface offers, so its violation ends the run.")

    def observe_served_model(self, served: str) -> None:
        """Record a served model id from any source, real-time or batch row, and re-check."""
        self.models_seen.append(served)
        self.assert_model_constant()

    # ------------------------------------------------------------------ the provider call

    def _call_anthropic(self, prompt: str, system: str):
        """The parent's call, with `response.model` kept and the payload recorded.

        The parent cannot be re-entered for this: it does not retain the SDK response, so the
        model id is gone by the time it returns. The call is therefore made here and the
        parent's truncation contract reproduced exactly — which is the duplication the
        parent-source-hash test in `tests/test_v18_client.py` exists to bind against drift.
        """
        self.assert_configured_model()
        if self._client is None:
            import os

            import anthropic
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            self._client = anthropic.Anthropic(api_key=key)

        payload = self.build_payload(prompt, system)
        msg = self._client.messages.create(**payload)   # type: ignore[attr-defined]

        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        in_tok = getattr(msg.usage, "input_tokens", 0)
        out_tok = getattr(msg.usage, "output_tokens", 0)
        stop = getattr(msg, "stop_reason", None)

        self.observe_served_model(getattr(msg, "model", "<absent>"))
        self.finish_reasons.append(str(stop))     # PF-6 guard: logged for every call
        self.output_lengths.append(len(text))
        self.payload_records.append({
            "payload_sha256": self.payload_digest(payload),
            "requested_model": payload["model"],
            "served_model": self.models_seen[-1],
            "max_tokens": payload["max_tokens"],
            "sampling_parameters": [],   # PF-9: none exist, and the record says so
            "stop_reason": str(stop),
            "input_tokens": in_tok, "output_tokens": out_tok,
        })

        if stop == "max_tokens" or not text.strip():
            raise LLMTruncatedError(
                f"truncated/empty completion (stop_reason={stop!r}, out_tok={out_tok}, "
                f"max_tokens={self.max_tokens}, text_len={len(text)})")
        return text, in_tok, out_tok

    # ------------------------------------------------------------------------ reporting

    def pin_record(self) -> dict:
        """PF-5's pin, in the form the manifest carries it."""
        return {
            "requested_model": self.model,
            "served_models": sorted(set(self.models_seen)),
            "served_model_constant": len(set(self.models_seen)) <= 1,
            "n_calls_observed": len(self.models_seen),
            "run_window_utc": [self.started_utc,
                               time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())],
            "sampling_parameters": {
                "sent": [],
                "_note": ("PF-9: the pinned model accepts no temperature; no parameter-based "
                          "determinism claim exists anywhere in v1.8"),
            },
        }


def guarded_cost_check(client: LLMClient, n_calls: int) -> None:
    """Pre-flight the shared cost guard for a whole batch rather than per call.

    Batch submission hands thousands of requests to the API at once, so the parent's per-call
    guard never sees them individually. This raises the same exception the parent would, before
    anything is submitted — the guard has to keep binding in batch mode or PF-4's raise to 150
    is decorative.
    """
    if client.calls + n_calls > client.max_llm_calls:
        raise CostGuardExceeded(
            f"max_llm_calls={client.max_llm_calls} would be exceeded by {n_calls} requests "
            f"({client.calls} already made)")
    if client.est_usd > client.max_usd:
        raise CostGuardExceeded(
            f"max_usd={client.max_usd} exceeded (est ${client.est_usd:.2f})")
