"""LLM gateway: the only place a model is called (AGENTS.md rule 2, Architecture 9).

- Prompts are versioned files in content/prompts/<prompt_key>.md, hashed into prompt_version.
- Output is parsed into a Pydantic schema. Free text never leaves the gateway unchecked.
- fixture mode replays recorded responses from content/fixtures/llm/<prompt_key>/<input_hash>.json
  and fails loudly when one is missing. Fixtures are recorded from real outputs, never hand-written.
- live mode needs settings.llm_live_approved (open decision 8) and a provider: the OpenAI adapter
  (openai_provider.py, REST via httpx, key from OPENAI_API_KEY) or one set with set_provider().
- A schema failure is retried once with the validation error, then raised.
- Every call is logged to llm_call (cost and latency, NFR-COST-01).
- Not implemented yet: the response cache keyed on (prompt_version, model, input_hash).
"""

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.llm_gateway.models import LLMCall, PromptVersion

T = TypeVar("T", bound=BaseModel)

DATA_OPEN = "<<<DATA"
DATA_CLOSE = "DATA>>>"


class GatewayError(Exception):
    """Base class; callers map these to problem+json."""


class FixtureMissing(GatewayError):
    pass


class LiveModeDisabled(GatewayError):
    pass


class OutputInvalid(GatewayError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class LLMProvider(Protocol):
    def complete(self, system: str, user: str, json_schema: dict[str, Any]) -> ProviderResult: ...


_provider: LLMProvider | None = None


def set_provider(provider: LLMProvider | None) -> None:
    global _provider
    _provider = provider


def _default_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider != "openai" or not settings.openai_api_key:
        raise LiveModeDisabled(
            "No LLM provider is configured. Set LLM_PROVIDER=openai and OPENAI_API_KEY."
        )
    from app.modules.llm_gateway.openai_provider import OpenAIProvider  # avoids a circular import

    return OpenAIProvider(settings.openai_api_key, settings.llm_model)


def input_hash(inputs: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def load_prompt(prompt_key: str) -> tuple[str, str]:
    """Return (text, sha256). The key may not contain path separators."""
    if not prompt_key.replace("_", "").replace(".", "").isalnum():
        raise GatewayError(f"Invalid prompt key: {prompt_key!r}")
    path = Path(get_settings().content_dir) / "prompts" / f"{prompt_key}.md"
    if not path.is_file():
        raise GatewayError(f"Prompt file not found: {prompt_key}")
    text = path.read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()


def delimit(name: str, text: str) -> str:
    """Wrap untrusted text (trainer uploads, topics) so the prompt can treat it as data only."""
    cleaned = text.replace(DATA_OPEN, "").replace(DATA_CLOSE, "")
    return f"{DATA_OPEN} {name}\n{cleaned}\n{DATA_CLOSE}"


def _prompt_version(db: Session, prompt_key: str, text: str, digest: str) -> PromptVersion:
    row = db.scalar(select(PromptVersion).where(PromptVersion.content_hash == digest))
    if row is None:
        row = PromptVersion(prompt_key=prompt_key, content_hash=digest, content=text)
        db.add(row)
        db.flush()
    return row


def _fixture(prompt_key: str, digest: str) -> ProviderResult:
    path = Path(get_settings().content_dir) / "fixtures" / "llm" / prompt_key / f"{digest}.json"
    if not path.is_file():
        raise FixtureMissing(
            f"No recorded fixture for {prompt_key} input {digest[:12]}. "
            "Record one from a real run; do not write it by hand."
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    return ProviderResult(text=json.dumps(record["response"]), model=record.get("model", "fixture"))


def complete_structured(
    db: Session, *, prompt_key: str, inputs: dict[str, Any], schema: type[T], stage: str
) -> T:
    """Run a prompt and return validated output. `stage` tags the llm_call row."""
    settings = get_settings()
    text, digest = load_prompt(prompt_key)
    version = _prompt_version(db, prompt_key, text, digest)
    in_hash = input_hash(inputs)
    user = json.dumps(inputs, sort_keys=True, ensure_ascii=False)
    json_schema = schema.model_json_schema()

    error: str | None = None
    for attempt in range(2):
        started = time.monotonic()
        if settings.llm_mode == "fixture":
            result = _fixture(prompt_key, in_hash)
        else:
            if not settings.llm_live_approved:
                raise LiveModeDisabled(
                    "Live LLM calls are disabled until the organisation approves "
                    "submission-data handling (open decision 8)."
                )
            provider = _provider or _default_provider()
            prompt = (
                text if error is None else f"{text}\n\nYour previous output was invalid: {error}"
            )
            result = provider.complete(prompt, user, json_schema)
        db.add(
            LLMCall(
                stage=stage,
                model=result.model,
                prompt_version_id=version.id,
                input_hash=in_hash,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                cost_usd=result.cost_usd,
                latency_ms=int((time.monotonic() - started) * 1000),
                cache_hit=False,
            )
        )
        try:
            return schema.model_validate_json(result.text)
        except ValidationError as exc:
            error = str(exc)
            if settings.llm_mode == "fixture":
                break  # a recorded fixture will not change on retry
    raise OutputInvalid(f"Model output did not match the {schema.__name__} schema: {error}")
