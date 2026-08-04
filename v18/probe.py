"""v1.8 §2 — the determinism probe, built so that it can fail.

The drafted probe could not. `LLMClient.complete()` keys its cache on
`(model, system, prompt, temperature, max_tokens)` and returns the stored text on a hit, so
three repeats of one prompt returned repeat 1's bytes and the probe reported "byte-identical"
for any model, always (Gate 0 finding G2, ruled PF-2). Two mechanisms fix it here, and the
second is the one that matters:

1. **Bypass.** `ProbeClient` gives the client a scratch cache directory **and empties it after
   every call**. The first attempt at this only did the former, and the assertion below caught
   it on the first run: repeat 1 wrote to the scratch directory and repeats 2-3 read it back,
   reproducing G2 inside the very code written to fix G2 (120 cache hits on 180 calls). The
   ruling's words were "read nothing, write nothing"; a fresh directory is not that.
2. **Assertion.** `run_probe()` asserts `cache_hits == 0` and
   `fresh_calls == prompts * repeats`. This is the mechanism that turned a silent wrong answer
   into a loud failure, exactly as the ruling anticipated.

**Why the cache is emptied rather than disabled.** Disabling it means editing
`src/llm/client.py`, which §10 does not authorise. Emptying after each call keeps the request
shape *identical to the real run's* by construction — the probe issues calls through the same
`LLMClient` the run uses, so it cannot measure a different request than the one that will be
made. A hand-rolled SDK path would be literally compliant and a second procedure for one
quantity (A5b), which is the trade the programme has repeatedly declined.

**`response.model` is NOT captured here, and cannot be (finding G10).** `LLMClient._call_anthropic`
returns `(text, input_tokens, output_tokens)` and discards `msg.model`; its cache record stores
`self.model`, the *requested* id. Reading that back would confirm the pin against itself. So
this module records the requested id only, and PF-5's per-call served-model assertion is
reported as unimplementable without an edit outside `v18/`.

Nothing in this module runs at import. It spends only when `run_probe` is called, and only on
the dev split.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from src.llm.client import LLMClient

#: §2/PF-1 — the hard ceiling on dev probe spend, across all probes in the run.
PROBE_CALL_BUDGET = 1000

#: §2 — repeats per prompt.
PROBE_REPEATS = 3


class ProbeBudgetExceeded(RuntimeError):
    """Raised before a call that would breach `PROBE_CALL_BUDGET`. Checked, never discovered."""


class ProbeCacheLeak(AssertionError):
    """A repeat was served from cache. The probe is invalid; do not read its verdict."""


class ModelPinViolation(AssertionError):
    """`response.model` changed mid-run. APPARATUS-STOP per §2 (PF-5)."""


class ProbeClient:
    """An `LLMClient` wrapper that never reads or writes the shared response cache.

    The wrapper owns a temporary cache directory rather than disabling caching inside
    `LLMClient`, because disabling it there would mean editing `src/llm/client.py` — outside
    v18 paths, which §10 does not authorise (the one authorised exception is the cost guard).
    A per-probe scratch directory achieves the same measurement without touching shared code.
    """

    def __init__(self, cfg: dict, budget: int = PROBE_CALL_BUDGET):
        self._dir = Path(tempfile.mkdtemp(prefix="v18_probe_cache_"))
        guard = cfg.get("cost_guard", {})
        llm_cfg = cfg["llm"]
        self.client = LLMClient(
            provider=llm_cfg["provider"], model=llm_cfg["model"],
            temperature=llm_cfg.get("temperature", 0.0),
            max_tokens=llm_cfg.get("max_tokens", 1024),
            cache_dir=self._dir,
            max_llm_calls=guard.get("max_llm_calls", 100_000),
            max_usd=guard.get("max_usd", 25.0))
        self.budget = budget
        #: The id v18 *asked* for. Not `response.model` — see the module docstring, finding G10.
        self.requested_model = llm_cfg["model"]

    def complete(self, prompt: str, system: str = "") -> str:
        if self.client.calls + 1 > self.budget:
            raise ProbeBudgetExceeded(
                f"probe budget {self.budget} would be exceeded (§2, PF-1); "
                f"{self.client.calls} calls already made")
        text = self.client.complete(prompt, system)
        # THE BYPASS. `LLMClient.complete` writes every fresh response to its cache directory,
        # so without this the next repeat of the same prompt is a hit and the probe measures the
        # cache. Emptying the scratch directory after each call is what makes "write nothing"
        # true in effect. The directory is the probe's alone, so wiping it is safe.
        for path in self._dir.glob("*.json"):
            path.unlink(missing_ok=True)
        return text

    @property
    def fresh_calls(self) -> int:
        return self.client.calls

    @property
    def cache_hits(self) -> int:
        return self.client.cache_hits

    def dispose(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)


def run_probe(prompts: list[tuple[str, str]], client: ProbeClient,
              repeats: int = PROBE_REPEATS) -> dict:
    """Issue every prompt `repeats` times and report whether all repeats agreed byte for byte.

    `prompts` is a list of `(system, prompt)` pairs. Returns the verdict plus the accounting
    that makes the verdict trustworthy: fresh calls, cache hits (which must be zero), and the
    set of served model ids.
    """
    assert repeats >= 2, "a determinism probe needs at least two repeats"
    expected = len(prompts) * repeats
    if expected > client.budget:
        raise ProbeBudgetExceeded(
            f"{len(prompts)} prompts x {repeats} repeats = {expected} calls exceeds the "
            f"{client.budget}-call probe budget (§2, PF-1)")

    divergent, outputs = [], []
    for index, (system, prompt) in enumerate(prompts):
        seen = [client.complete(prompt, system) for _ in range(repeats)]
        outputs.append(seen)
        if any(text != seen[0] for text in seen[1:]):
            divergent.append(index)

    # PF-2's assertion. A cached repeat means the probe measured the cache, not the model.
    if client.cache_hits != 0:
        raise ProbeCacheLeak(
            f"{client.cache_hits} probe repeat(s) served from cache; the bypass failed and the "
            f"verdict is invalid (§2, PF-2).")
    if client.fresh_calls != expected:
        raise ProbeCacheLeak(
            f"fresh calls {client.fresh_calls} != prompts x repeats {expected}; the probe did "
            f"not issue an independent call per repeat (§2, PF-2).")

    return {
        "prompts": len(prompts), "repeats": repeats,
        "fresh_calls": client.fresh_calls, "cache_hits": client.cache_hits,
        "byte_identical": not divergent,
        "divergent_prompt_indices": divergent,
        "n_divergent": len(divergent),
        "requested_model": client.requested_model,
        "_served_model_note": ("response.model is not recoverable through LLMClient "
                               "(finding G10); this is the REQUESTED id"),
        "_note": ("byte_identical=True selects the single-run branch; False selects §2's "
                  "targeted-repeat fallback (PF-3)"),
    }
