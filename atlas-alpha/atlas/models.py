"""
Atlas Core Models
All financial data structures with strict schema validation.
Every evidence carries Point-in-Time discipline.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Enums
# =============================================================================
class DivergenceType(str, Enum):
    STOCK_VS_SECTOR = "stock_vs_sector"
    STOCK_VS_MARKET = "stock_vs_market"
    PRICE_VS_EARNINGS = "price_vs_earnings"
    PRICE_VS_FUNDAMENTAL = "price_vs_fundamental"
    PRICE_VS_FLOW = "price_vs_flow"
    CURRENT_VS_HISTORICAL = "current_vs_historical"


class EvidenceDirection(str, Enum):
    SUPPORT = "support"
    CONTRADICT = "contradict"
    NEUTRAL = "neutral"


class InvestigationStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    REVIEWING = "reviewing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"


# =============================================================================
# Point-in-Time Evidence
# =============================================================================
class Evidence(BaseModel):
    """
    Every piece of evidence must carry strict temporal metadata.
    This prevents the #1 failure mode in financial AI: temporal leakage.
    """
    model_config = ConfigDict(strict=True)

    source: str = Field(..., description="Data source name")
    content: str = Field(..., description="Evidence content")
    published_at: datetime = Field(..., description="When the event occurred")
    available_at: datetime = Field(..., description="When data became available to system")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow, description="When system fetched it")
    content_hash: Optional[str] = Field(None, description="SHA256 hash for integrity")
    direction: EvidenceDirection = Field(default=EvidenceDirection.NEUTRAL)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Source reliability")

    def is_valid_for_backtest(self, simulation_date: datetime) -> bool:
        """Strict PIT check: evidence must be available before simulation date."""
        return self.available_at <= simulation_date

    def temporal_summary(self) -> str:
        return f"published:{self.published_at.isoformat()} | available:{self.available_at.isoformat()}"


# =============================================================================
# Divergence Signal
# =============================================================================
class DivergenceSignal(BaseModel):
    """
    Output of Divergence Engine.
    100% deterministic — no LLM involved in generation.
    """
    model_config = ConfigDict(strict=True)

    ticker: str
    date: datetime
    divergence_type: DivergenceType
    severity: float = Field(..., ge=0.0, le=1.0, description="0=minor, 1=critical")
    z_score: float = Field(..., description="Statistical anomaly score")
    stock_return: float = Field(..., description="Stock daily return (%)")
    sector_return: float = Field(..., description="Sector/index daily return (%)")
    description: str = Field(..., description="Human-readable explanation")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Raw audit data")

    def is_actionable(self, threshold: float = 0.7) -> bool:
        return self.severity >= threshold

    def one_liner(self) -> str:
        return f"[{self.date.date()}] {self.ticker}: {self.divergence_type.value} | severity={self.severity:.0%} | z={self.z_score:.2f}"


# =============================================================================
# Thesis Tree
# =============================================================================
class ThesisNode(BaseModel):
    """
    A single node in the investment hypothesis tree.
    Not a report — a living, monitored assumption.
    """
    model_config = ConfigDict(strict=True)

    node_id: str
    ticker: str
    hypothesis: str = Field(..., description="The core assumption, e.g. 'Europe sales grow >10%'")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Current confidence (0-100)")
    key_variables: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence IDs")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Evidence IDs")
    overturn_conditions: List[str] = Field(default_factory=list, description="What would falsify this")
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_at_risk(self) -> bool:
        return self.confidence < 60

    def is_falsified(self) -> bool:
        return self.confidence < 30

    def impact_summary(self) -> str:
        status = "🔴 FALSIFIED" if self.is_falsified() else ("🟡 AT RISK" if self.is_at_risk() else "🟢 STABLE")
        return f"{status} {self.hypothesis} (confidence: {self.confidence:.0f})"


class ThesisTree(BaseModel):
    """Complete thesis tree for a single stock."""
    model_config = ConfigDict(strict=True)

    ticker: str
    overall_direction: str = Field(default="neutral", description="bullish / neutral / bearish")
    nodes: Dict[str, ThesisNode] = Field(default_factory=dict)
    root_id: Optional[str] = None

    def get_node(self, node_id: str) -> Optional[ThesisNode]:
        return self.nodes.get(node_id)

    def at_risk_nodes(self) -> List[ThesisNode]:
        return [n for n in self.nodes.values() if n.is_at_risk()]

    def update_confidence(self, node_id: str, new_confidence: float, reason: str = "") -> ThesisNode:
        """Update confidence with audit trail."""
        node = self.nodes[node_id]
        node.confidence = max(0.0, min(100.0, new_confidence))
        node.updated_at = datetime.utcnow()
        return node

    def tree_view(self) -> str:
        """ASCII tree visualization."""
        lines = [f"📊 {self.ticker} | Overall: {self.overall_direction.upper()}"]
        lines.append("=" * 50)

        def render(node_id: str, depth: int = 0):
            node = self.nodes.get(node_id)
            if not node:
                return
            indent = "    " * depth
            icon = "🔴" if node.is_falsified() else ("🟡" if node.is_at_risk() else "🟢")
            lines.append(f"{indent}{icon} [{node.confidence:.0f}] {node.hypothesis}")
            for child_id in node.children_ids:
                render(child_id, depth + 1)

        if self.root_id:
            render(self.root_id)
        else:
            for node in self.nodes.values():
                if not node.parent_id:
                    render(node.node_id)
        return "\n".join(lines)


# =============================================================================
# Agent Outputs
# =============================================================================
class Hypothesis(BaseModel):
    """A candidate explanation for an anomaly."""
    model_config = ConfigDict(strict=True)

    id: str = Field(..., pattern=r"^H[0-9]+$")
    text: str = Field(..., description="The explanation")
    confidence: float = Field(..., ge=0.0, le=100.0, description="LLM-assessed likelihood")
    evidence_needed: List[str] = Field(default_factory=list)
    evidence_found: List[str] = Field(default_factory=list)
    status: str = Field(default="pending", description="pending / verified / rejected")


class InvestigationReport(BaseModel):
    """Structured output from Investigation Agent."""
    model_config = ConfigDict(strict=True)

    signal: DivergenceSignal
    hypotheses: List[Hypothesis]
    leading_hypothesis: str = Field(..., description="ID of most likely hypothesis")
    thesis_impact: str = Field(..., description="How this affects existing investment thesis")
    evidence_summary: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def leading(self) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.id == self.leading_hypothesis:
                return h
        return None


class ReviewResult(BaseModel):
    """Output from Reviewer Agent — deliberately adversarial."""
    model_config = ConfigDict(strict=True)

    report_id: str
    issues_found: List[str] = Field(default_factory=list)
    numerical_errors: List[str] = Field(default_factory=list)
    evidence_conflicts: List[str] = Field(default_factory=list)
    temporal_leakage_risk: List[str] = Field(default_factory=list)
    confidence_adjustment: float = Field(default=0.0, description="How much to discount report confidence")
    verdict: str = Field(..., description="PASS / PASS_WITH_CAUTION / FAIL")

    def has_critical_issues(self) -> bool:
        return len(self.numerical_errors) > 0 or len(self.temporal_leakage_risk) > 0


# =============================================================================
# Orchestration State
# =============================================================================
class InvestigationState(BaseModel):
    """Complete state of an investigation run."""
    model_config = ConfigDict(strict=True)

    run_id: str
    ticker: str
    signal: DivergenceSignal
    report: Optional[InvestigationReport] = None
    review: Optional[ReviewResult] = None
    status: InvestigationStatus = InvestigationStatus.DETECTED
    human_decision: Optional[str] = None  # approved / modified / rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
