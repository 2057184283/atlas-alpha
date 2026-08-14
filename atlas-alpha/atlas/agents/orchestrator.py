"""
Orchestrator
============
The conductor. Decides whether an anomaly deserves investigation,
routes tasks, and enforces human approval gates.

Two hard rules:
1. AI cannot modify formal thesis without human approval
2. AI cannot change earnings forecasts without human approval

This is B-grade product logic, not a toy.
"""

from typing import Optional
from datetime import datetime
import uuid

from atlas.models import (
    DivergenceSignal, InvestigationState, InvestigationStatus,
    InvestigationReport, ReviewResult
)
from atlas.engines.divergence import DivergenceEngine
from atlas.engines.thesis import ThesisEngine
from atlas.agents.investigator import InvestigationAgent
from atlas.agents.reviewer import ReviewerAgent


class Orchestrator:
    """
    Routes anomalies through the full pipeline:
    Detect → Decide → Investigate → Review → Human Gate → Update Thesis
    """

    def __init__(
        self,
        divergence_engine: Optional[DivergenceEngine] = None,
        thesis_engine: Optional[ThesisEngine] = None,
        investigator: Optional[InvestigationAgent] = None,
        reviewer: Optional[ReviewerAgent] = None,
    ):
        self.divergence = divergence_engine or DivergenceEngine()
        self.thesis = thesis_engine or ThesisEngine()
        self.investigator = investigator or InvestigationAgent()
        self.reviewer = reviewer or ReviewerAgent()

    def run(
        self,
        stock_df,
        sector_df,
        ticker: str = "CATL",
        market_df=None,
        skip_human_gate: bool = False,
    ) -> InvestigationState:
        """
        Full pipeline execution.

        Args:
            skip_human_gate: For demo/testing only. In production, always False.
        """
        run_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Step 1: Detect
        print(f"\n[1/6] Divergence Detection")
        signals = self.divergence.detect_all(stock_df, sector_df, market_df)

        if not signals:
            print("      No actionable divergence detected.")
            return InvestigationState(
                run_id=run_id,
                ticker=ticker,
                signal=DivergenceSignal(
                    ticker=ticker,
                    date=datetime.utcnow(),
                    divergence_type="stock_vs_sector",
                    severity=0.0,
                    z_score=0.0,
                    stock_return=0.0,
                    sector_return=0.0,
                    description="No signal",
                ),
                status=InvestigationStatus.COMPLETED,
            )

        signal = signals[0]
        print(f"      ✅ {signal.one_liner()}")

        state = InvestigationState(
            run_id=run_id,
            ticker=ticker,
            signal=signal,
            status=InvestigationStatus.INVESTIGATING,
        )

        # Step 2: Load thesis context
        print(f"\n[2/6] Loading Thesis Tree")
        tree = self.thesis.load(ticker)
        print(f"      {tree.ticker} | Direction: {tree.overall_direction.upper()}")
        print(f"      At-risk nodes: {len(tree.at_risk_nodes())}")

        # Step 3: Investigate
        print(f"\n[3/6] Investigation Agent")
        context = tree.tree_view()
        report = self.investigator.investigate(signal, context=context)
        state.report = report
        state.status = InvestigationStatus.REVIEWING

        print(f"      Leading hypothesis: {report.leading_hypothesis}")
        print(f"      Thesis impact: {report.thesis_impact[:80]}...")

        # Step 4: Review
        print(f"\n[4/6] Reviewer Agent (Adversarial)")
        review = self.reviewer.review(report)
        state.review = review

        print(f"      Verdict: {review.verdict}")
        if review.numerical_errors:
            print(f"      ⚠️  Numerical errors: {len(review.numerical_errors)}")
        if review.temporal_leakage_risk:
            print(f"      ⚠️  Temporal leakage risk: {len(review.temporal_leakage_risk)}")
        if review.evidence_conflicts:
            print(f"      ⚠️  Evidence conflicts: {len(review.evidence_conflicts)}")

        # Step 5: Human Approval Gate
        print(f"\n[5/6] Human Approval Gate")
        if review.verdict == "FAIL":
            print("      ❌ Review FAILED. Investigation rejected.")
            state.status = InvestigationStatus.REJECTED
            return state

        if skip_human_gate:
            print("      [DEMO MODE] Auto-approved")
            state.human_decision = "approved"
        else:
            print("      ⏸️  PAUSED for human approval")
            print(f"      Proposed action: Update thesis based on {report.leading_hypothesis}")
            print(f"      Impact: {report.thesis_impact}")
            print(f"      Type 'approved', 'modified', or 'rejected':")
            # In real usage, this would be an API endpoint or UI button
            state.status = InvestigationStatus.WAITING_APPROVAL
            return state

        # Step 6: Update Thesis (only if approved)
        print(f"\n[6/6] Updating Thesis")
        if state.human_decision == "approved":
            # Example: reduce confidence on most impacted node
            # In real system, this would use thesis_mapping skill
            leading = report.leading()
            if leading and "欧洲" in leading.text:
                node = self.thesis.update_node_confidence(
                    ticker=ticker,
                    node_id="H1",
                    new_confidence=max(30, tree.get_node("H1").confidence - 15),
                    reason=f"Divergence signal + {leading.text}",
                )
                print(f"      Updated H1 confidence: {node.confidence:.0f}")

            state.status = InvestigationStatus.COMPLETED
            state.completed_at = datetime.utcnow()

        return state

    def approve(self, state: InvestigationState, decision: str) -> InvestigationState:
        """
        Resume pipeline after human approval.
        """
        state.human_decision = decision

        if decision == "approved":
            # Re-run step 6
            tree = self.thesis.load(state.ticker)
            leading = state.report.leading()
            if leading and "欧洲" in leading.text:
                self.thesis.update_node_confidence(
                    ticker=state.ticker,
                    node_id="H1",
                    new_confidence=max(30, tree.get_node("H1").confidence - 15),
                    reason=f"Human-approved: {leading.text}",
                )
            state.status = InvestigationStatus.COMPLETED
            state.completed_at = datetime.utcnow()
        else:
            state.status = InvestigationStatus.REJECTED

        return state
