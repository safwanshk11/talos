from app.core.config import settings
from app.services.ai.base import AIProvider, AIProviderError


def get_ai_provider() -> AIProvider:
    """Instantiate the configured AIProvider. The rest of TALOS depends only on the
    AIProvider interface, never on this factory or a concrete implementation."""
    provider = (settings.AI_PROVIDER or "").lower()

    if provider == "ollama":
        from app.services.ai.ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.AI_MODEL or "qwen2.5:7b",
            timeout=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise AIProviderError("GEMINI_API_KEY is not configured; cannot use the Gemini AI provider.")
        from app.services.ai.gemini_provider import GeminiProvider

        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            timeout=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )

    raise AIProviderError(f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. Expected 'ollama' or 'gemini'.")
