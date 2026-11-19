"""OpenAI adapter for the LLM gateway. Only the gateway imports this module (AGENTS.md rule 2).

Uses the REST API through httpx, so no provider SDK is added. The API key comes from
OPENAI_API_KEY and is never logged or stored.
"""

from typing import Any

import httpx

from app.modules.llm_gateway.service import GatewayError, ProviderResult


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def complete(self, system: str, user: str, json_schema: dict[str, Any]) -> ProviderResult:
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": json_schema, "strict": False},
            },
        }
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                json=body,
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            # Status only: the body can echo prompt content.
            raise GatewayError(f"OpenAI returned HTTP {exc.response.status_code}") from None
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            raise GatewayError("OpenAI request failed or returned an unexpected response") from None
        usage = data.get("usage", {})
        return ProviderResult(
            text=text or "",
            model=data.get("model", self._model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            cost_usd=0.0,  # pricing is not configured yet; tokens are recorded
        )
