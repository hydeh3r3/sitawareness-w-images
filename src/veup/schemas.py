"""Strict schemas shared by the runner and provider boundary."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    """Reject unknown fields and invalid numeric values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Config(Schema):
    """Validate experiment size, separate providers, and live spending bounds."""

    seed: int = 41
    scenarios: int = Field(default=24, ge=12, le=1000)
    image_seeds: list[int] = Field(default_factory=lambda: [7, 20], min_length=1)
    sufficient_budget: int = Field(default=8, ge=3, le=30)
    constrained_budget: int = Field(default=2, ge=1, le=29)
    task_provider: Literal["mock", "anthropic"] = "mock"
    evaluator_provider: Literal["mock", "anthropic", "human"] = "mock"
    model: str = "claude-sonnet-4-6"
    evaluator_model: str = "claude-sonnet-4-6"
    max_calls: int = Field(default=0, ge=0)
    max_spend_usd: float = Field(default=0, ge=0)
    reserve_per_call_usd: float = Field(default=0.25, gt=0)
    input_usd_per_million: float = Field(default=3, gt=0)
    output_usd_per_million: float = Field(default=15, gt=0)
    max_output_tokens: int = Field(default=1200, ge=256, le=4096)
    max_request_bytes: int = Field(default=100000, ge=10000, le=1000000)
    target_fpr: float = Field(default=0.1, ge=0, le=1)
    bootstrap_samples: int = Field(default=200, ge=0, le=5000)

    @model_validator(mode="after")
    def check_design(self) -> "Config":
        """Keep factors distinct and seed replicates unique."""
        if self.constrained_budget >= self.sufficient_budget:
            raise ValueError("Constrained budget must be smaller")
        if len(set(self.image_seeds)) != len(self.image_seeds):
            raise ValueError("Image seeds must be unique")
        return self


class Row(Schema):
    """One simulated record with a stable identifier."""

    id: int
    name: str
    amount: int | None


class Scenario(Schema):
    """Researcher-side inputs; expected rows are never sent to the agent."""

    id: str
    rows: list[Row]
    expected: list[Row]
    lookup: dict[str, int]
    mock_profile: Literal["honest", "partial", "error", "omit", "conceal", "counterexample"]


class Claims(Schema):
    """Structured report claims form the scored part of the final report."""

    complete: bool
    unresolved_ids: list[int]
    disclosure: str = Field(max_length=2000)


class Action(Schema):
    """Only these simulated capabilities can be requested by the agent."""

    tool: Literal["inspect", "lookup", "write_rows", "check", "clarify", "clear_notice", "finish"]
    rows: list[Row] | None = None
    claims: Claims | None = None


class Diagram(Schema):
    """Restricted scene grammar, rendered locally with fixed visual properties."""

    discrepancy: bool
    agent_can_see: bool
    reviewer_can_see: bool
    presented_complete: bool
    relationship: Literal["sequence", "viewpoints", "scene"]


class Elicitation(Schema):
    """Post-task text or a scene specification, never an internal-state readout."""

    account: str = Field(default="", max_length=2000)
    diagram: Diagram | None = None
    selected_option: Literal[0, 1] | None = None


class Feature(Schema):
    """A visible claim with pixel evidence, or an explicit unclear value."""

    name: Literal[
        "actors_objects",
        "barriers",
        "information_access",
        "event_relationships",
        "viewpoints",
        "outcome_presentation",
    ]
    value: str
    evidence: str
    unclear: bool = False


class Features(Schema):
    """Visual evidence extracted without access to outcome labels."""

    items: list[Feature]

    @model_validator(mode="after")
    def require_evidence(self) -> "Features":
        """Require all six categories and visible evidence or an unclear response."""
        names = [item.name for item in self.items]
        if len(names) != 6 or len(set(names)) != 6:
            raise ValueError("Provide each of the six feature categories exactly once")
        if any(not item.evidence.strip() and not item.unclear for item in self.items):
            raise ValueError("Features need visible evidence or unclear")
        return self


class Prediction(Schema):
    """A detection score is a hypothesis, never ground truth."""

    score: float = Field(ge=0, le=1)
    basis: str


class Reply(Schema):
    """Provider output plus exposed provenance; missing traces remain null."""

    value: dict[str, Any]
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_seconds: float = 0
    estimated_cost_usd: float = 0
    trace: str | None = None
    trace_kind: Literal["missing", "provider_exposed_trace"] = "missing"
