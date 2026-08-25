from abc import ABC, abstractmethod

from app.services.ai.schemas import ProblemAnalysis, MaintenancePlan, PatchGenerationResult


class AIProviderError(Exception):
    """Raised when an AI provider is unavailable, times out, or cannot produce
    valid structured output after its retry budget is exhausted."""


class AIProvider(ABC):
    """Provider-agnostic reasoning interface. TALOS's orchestration code (PatchService)
    only ever talks to this interface — it must not need to know whether the
    concrete implementation is Ollama, Gemini, or anything else."""

    name: str
    model: str

    @abstractmethod
    async def analyze_problem(self, context: str) -> ProblemAnalysis:
        """Ground the model in the maintenance context and produce a root-cause
        understanding before any plan is proposed."""

    @abstractmethod
    async def generate_plan(self, context: str, analysis: ProblemAnalysis) -> MaintenancePlan:
        """Produce a structured, schema-validated maintenance plan."""

    @abstractmethod
    async def generate_patch(self, context: str, plan: MaintenancePlan) -> PatchGenerationResult:
        """Produce source file edits for files the plan authorized (beyond the
        deterministic dependency-manifest update, which never goes through the model)."""
