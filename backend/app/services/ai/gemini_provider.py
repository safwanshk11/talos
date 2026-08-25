import asyncio
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.services.ai.base import AIProvider, AIProviderError
from app.services.ai.schemas import ProblemAnalysis, MaintenancePlan, PatchGenerationResult
from app.services.ai.prompts import SYSTEM_PROMPT, ANALYZE_TASK, PLAN_TASK, PATCH_TASK

logger = logging.getLogger("talos.ai.gemini")

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    """Hosted reasoning via Google's Gemini API, used for deployment. Uses Gemini's
    native structured-output mode (response_schema) so output is JSON-schema
    constrained the same way the Ollama provider is."""

    def __init__(self, api_key: str, model: str, timeout: float = 180.0, max_retries: int = 2):
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise AIProviderError(
                "google-generativeai package is not installed; add it to requirements.txt."
            ) from exc

        genai.configure(api_key=api_key)
        self._genai = genai
        self._client = genai.GenerativeModel(model, system_instruction=SYSTEM_PROMPT)
        self.model = model
        self.name = "gemini"
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

    async def _call_structured(self, prompt: str, schema_model: Type[T]) -> T:
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.generate_content,
                        prompt,
                        generation_config=self._genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=schema_model,
                            temperature=0.1,
                        ),
                    ),
                    timeout=self.timeout,
                )
                return schema_model.model_validate_json(response.text)
            except asyncio.TimeoutError as exc:
                raise AIProviderError(f"Gemini provider timed out after {self.timeout}s") from exc
            except ValidationError as exc:
                last_error = exc
                logger.warning(f"Gemini structured output invalid (attempt {attempt + 1}): {exc}")
                prompt = (
                    f"{prompt}\n\nYour previous response was invalid ({exc}). "
                    "Respond again with ONLY a valid JSON object matching the required schema."
                )
            except Exception as exc:
                raise AIProviderError(f"Gemini provider request failed: {exc}") from exc

        raise AIProviderError(
            f"Gemini provider failed to produce valid structured output after {self.max_retries} attempts: {last_error}"
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
