import json
import logging
from typing import Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.services.ai.base import AIProvider, AIProviderError
from app.services.ai.schemas import ProblemAnalysis, MaintenancePlan, PatchGenerationResult
from app.services.ai.prompts import SYSTEM_PROMPT, ANALYZE_TASK, PLAN_TASK, PATCH_TASK

logger = logging.getLogger("talos.ai.ollama")

T = TypeVar("T", bound=BaseModel)


class OllamaProvider(AIProvider):
    """Local reasoning via Ollama's structured-output (JSON schema) chat API.
    Used for local development/testing where no hosted API key is configured."""

    def __init__(self, base_url: str, model: str, timeout: float = 180.0, max_retries: int = 2):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = "ollama"
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

    async def _call_structured(self, prompt: str, schema_model: Type[T]) -> T:
        schema = schema_model.model_json_schema()
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt},
                            ],
                            "format": schema,
                            "stream": False,
                            "options": {"temperature": 0.1},
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    parsed = json.loads(content)
                    return schema_model.model_validate(parsed)
                except httpx.HTTPError as exc:
                    raise AIProviderError(f"Ollama provider unreachable at {self.base_url}: {exc}") from exc
                except (json.JSONDecodeError, ValidationError) as exc:
                    last_error = exc
                    logger.warning(f"Ollama structured output invalid (attempt {attempt + 1}): {exc}")
                    prompt = (
                        f"{prompt}\n\nYour previous response was invalid ({exc}). "
                        "Respond again with ONLY a valid JSON object matching the required schema."
                    )

        raise AIProviderError(
            f"Ollama provider failed to produce valid structured output after {self.max_retries} attempts: {last_error}"
        )

    async def analyze_problem(self, context: str) -> ProblemAnalysis:
        prompt = ANALYZE_TASK.format(context=context)
        return await self._call_structured(prompt, ProblemAnalysis)

    async def generate_plan(self, context: str, analysis: ProblemAnalysis) -> MaintenancePlan:
        prompt = PLAN_TASK.format(analysis=analysis.model_dump_json(indent=2), context=context)
        return await self._call_structured(prompt, MaintenancePlan)

    async def generate_patch(self, context: str, plan: MaintenancePlan) -> PatchGenerationResult:
        prompt = PATCH_TASK.format(plan=plan.model_dump_json(indent=2), context=context)
        return await self._call_structured(prompt, PatchGenerationResult)
