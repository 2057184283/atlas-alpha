"""
Reviewer Agent
==============
Deliberately adversarial. Attacks the investigation report.

This is the most unusual and valuable part of Atlas.
Most AI systems seek to confirm. Atlas seeks to falsify.

Checks:
1. Numerical errors (LLM sometimes misreads its own output)
2. Evidence conflicts (two hypotheses rely on contradictory facts)
3. Temporal leakage (using information from after the signal date)
4. Confirmation bias (ignoring disconfirming evidence)
5. Overconfidence (confidence not justified by evidence quality)
"""

import os
import json
from datetime import datetime

from openai import OpenAI

from atlas.models import InvestigationReport, ReviewResult


class ReviewerAgent:
    """
    The red team. Every investigation must pass adversarial review.

    If this agent finds critical issues, the report goes back for revision
    or is flagged for human review.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def review(self, report: InvestigationReport) -> ReviewResult:
        """
        Attack the investigation report from multiple angles.
        """
        prompt = self._build_prompt(report)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a skeptical senior research director. "
                        "Your job is to find flaws in analyst reports. "
                        "You are ruthless about numerical accuracy, logical consistency, "
                        "and evidence quality. You have prevented many bad investment decisions."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1500,
        )

        raw = json.loads(response.choices[0].message.content)

        return ReviewResult(
            report_id=f"{report.signal.ticker}_{report.signal.date.date()}",
            issues_found=raw.get("issues_found", []),
            numerical_errors=raw.get("numerical_errors", []),
            evidence_conflicts=raw.get("evidence_conflicts", []),
            temporal_leakage_risk=raw.get("temporal_leakage_risk", []),
            confidence_adjustment=float(raw.get("confidence_adjustment", 0)),
            verdict=raw.get("verdict", "PASS_WITH_CAUTION"),
        )

    def _build_prompt(self, report: InvestigationReport) -> str:
        hypotheses_text = "\n".join([
            f"{h.id}: {h.text} (confidence: {h.confidence}%)"
            for h in report.hypotheses
        ])

        return f"""## TASK
Review the following investigation report for errors, biases, and weaknesses.
Be ruthless. A bad report that passes review is worse than a good report that fails.

## ORIGINAL SIGNAL
- Ticker: {report.signal.ticker}
- Date: {report.signal.date.date()}
- Severity: {report.signal.severity:.1%}
- Z-score: {report.signal.z_score:+.2f}
- Stock: {report.signal.stock_return:+.1f}% | Sector: {report.signal.sector_return:+.1f}%

## INVESTIGATION REPORT
Leading Hypothesis: {report.leading_hypothesis}
Thesis Impact: {report.thesis_impact}

Hypotheses:
{hypotheses_text}

## REVIEW CHECKLIST
For each item, state whether you found issues and provide specifics.

1. **Numerical Errors**: Did the analyst misstate any numbers from the original signal?
2. **Evidence Conflicts**: Do any two hypotheses rely on contradictory assumptions?
3. **Temporal Leakage**: Does the report implicitly use information from AFTER {report.signal.date.date()}?
4. **Confirmation Bias**: Did the analyst ignore plausible alternative explanations?
5. **Overconfidence**: Are confidence levels justified by the stated evidence?

## OUTPUT FORMAT (strict JSON)
{{
  "issues_found": ["List of all issues found"],
  "numerical_errors": ["Any misstated numbers"],
  "evidence_conflicts": ["Contradictory assumptions between hypotheses"],
  "temporal_leakage_risk": ["Any hint of using future information"],
  "confidence_adjustment": -15,
  "verdict": "PASS" | "PASS_WITH_CAUTION" | "FAIL"
}}

## VERDICT CRITERIA
- PASS: No material issues. Report is reliable.
- PASS_WITH_CAUTION: Minor issues that don't invalidate conclusions. Adjust confidence down.
- FAIL: Critical errors (numerical, temporal leakage, or severe bias). Report must be redone.
"""
