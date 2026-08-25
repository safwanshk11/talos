from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProblemAnalysis(BaseModel):
    """Output of AIProvider.analyze_problem() — grounded understanding of the issue
    before any plan is proposed."""

    root_cause: str
    affected_component: str
    reasoning: str
    missing_information: List[str] = Field(default_factory=list)
    escalation_required: bool = False
    escalation_reason: str = ""


class MaintenancePlan(BaseModel):
    """Output of AIProvider.generate_plan() — machine-validated structured plan.

    target_version and files_to_modify are required (no defaults) so the model is
    forced to state them explicitly rather than silently omitting fields it is
    unsure about.
    """

    summary: str
    root_cause: str
    target_version: str  # dependency version to upgrade to, or "N/A" if not a dependency fix
    requires_code_changes: bool
    files_to_modify: List[str]
    actions: List[str]
    verification_recommendations: List[str]
    risk: RiskLevel
    risk_reason: str
    escalate: bool = False
    escalation_reason: str = ""


class FileEdit(BaseModel):
    path: str
    new_content: str
    reason: str


class PatchGenerationResult(BaseModel):
    """Output of AIProvider.generate_patch() — source file edits beyond the
    deterministic dependency-manifest update. Only files listed in the plan's
    files_to_modify may be touched; PatchService enforces this, not the model."""

    edits: List[FileEdit] = Field(default_factory=list)
    notes: str = ""
