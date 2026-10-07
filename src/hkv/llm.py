"""One structured request per item to the Claude API, or a whole backlog as one Message Batch (half price).

Used by hkv.debate and hkv.reservations: each builds the user message and the JSON schema; this sends it with thinking
off (the tasks are reading and summarising) and the system prompt cached, and returns the parsed JSON object.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence

log = logging.getLogger(__name__)

BATCH_POLL_SECONDS = 60


class JsonModel:
    def __init__(self, model: str, system: str, schema: dict, max_tokens: int = 8000):
        import anthropic  # imported here so the API and tests do not need the package

        self.client = anthropic.Anthropic()
        self.model, self.system, self.max_tokens = model, system, max_tokens
        self.output = {"format": {"type": "json_schema", "schema": schema}}

    def _params(self, content: str | list) -> dict:
        return dict(model=self.model, max_tokens=self.max_tokens, thinking={"type": "disabled"},
                    system=[{"type": "text", "text": self.system, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": content}], output_config=self.output)

    @staticmethod
    def _parse(message) -> dict:
        if message.stop_reason == "refusal":
            raise RuntimeError(f"refused: {message.stop_details}")
        if message.stop_reason == "max_tokens":
            raise RuntimeError("output cut at max_tokens")
        return json.loads(next(b.text for b in message.content if b.type == "text"))

    def ask(self, content: str | list) -> dict:
        return self._parse(self.client.messages.create(**self._params(content)))

    def ask_many(self, contents: Sequence[str | list]) -> list[dict | Exception]:
        batch = self.client.messages.batches.create(requests=[
            {"custom_id": str(i), "params": self._params(c)} for i, c in enumerate(contents)])
        log.info("message batch %s: %d requests", batch.id, len(contents))
        while batch.processing_status != "ended":
            time.sleep(BATCH_POLL_SECONDS)
            batch = self.client.messages.batches.retrieve(batch.id)
            c = batch.request_counts
            log.info("message batch %s: %d processing, %d succeeded, %d errored", batch.id, c.processing, c.succeeded, c.errored)
        out: list[dict | Exception] = [RuntimeError("missing from batch")] * len(contents)
        for r in self.client.messages.batches.results(batch.id):
            i = int(r.custom_id)
            try:
                if r.result.type != "succeeded":
                    raise RuntimeError(f"batch request {r.result.type}")
                out[i] = self._parse(r.result.message)
            except Exception as e:
                out[i] = e
        return out
