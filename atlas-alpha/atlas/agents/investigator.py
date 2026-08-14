"""
Investigation Agent
===================
Receives a divergence signal and generates structured hypotheses.

Role: Propose explanations, organize evidence, map to thesis.
Constraints:
- Must generate 5 competing hypotheses (prevent confirmation bias)
- Must use structured output (JSON mode)
- Must NOT hallucinate numbers — all metrics come from DivergenceEngine
"""

import os
import json
from typing import List
from datetime import datetime

from openai import OpenAI

from atlas.models import DivergenceSignal, InvestigationReport, Hypothesis


class InvestigationAgent:
    """
    LLM Agent that investigates market anomalies.

    Design choices:
    1. JSON mode for reliable structured output
    2. Low temperature (0.3) for consistency
    3. Explicitly forbidden from making up numbers
    4. Must propose 5 hypotheses (adversarial thinking)
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def investigate(self, signal: DivergenceSignal, context: str = "") -> InvestigationReport:
        """
        Main entry point. Given a divergence signal, produce a full investigation.
        """
        prompt = self._build_prompt(signal, context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior equity research analyst specializing in "
                        "the new energy sector. You are rigorous, evidence-based, "
                        "and always consider multiple explanations before concluding."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
        )

        raw = json.loads(response.choices[0].message.content)

        # Validate and construct
        hypotheses = [
            Hypothesis(
                id=h["id"],
                text=h["text"],
                confidence=float(h["confidence"]),
                evidence_needed=h.get("evidence_needed", []),
            )
            for h in raw.get("hypothesies", raw.get("hypotheses", []))
        ]

        return InvestigationReport(
            signal=signal,
            hypotheses=hypotheses,
            leading_hypothesis=raw.get("leading_hypothesis", "H1"),
            thesis_impact=raw.get("thesis_impact", ""),
            evidence_summary=raw.get("evidence_summary", ""),
            timestamp=datetime.utcnow(),
        )

    def _build_prompt(self, signal: DivergenceSignal, context: str) -> str:
        return f"""## TASK
You have received an automated market anomaly signal. Your job is to generate a structured investigation report.

## SIGNAL DETAILS (DO NOT QUESTION THESE NUMBERS — they come from deterministic calculation)
- Ticker: {signal.ticker}
- Date: {signal.date.date()}
- Divergence Type: {signal.divergence_type.value}
- Severity: {signal.severity:.1%}
- Statistical Z-score: {signal.z_score:+.2f}
- Stock Return: {signal.stock_return:+.1f}%
- Sector Return: {signal.sector_return:+.1f}%
- Description: {signal.description}

## CONTEXT
{context if context else "No additional context provided."}

## INSTRUCTIONS
1. Generate exactly 5 competing hypotheses (H1-H5) that could explain this anomaly.
2. Each hypothesis must be falsifiable — include what evidence would confirm or reject it.
3. Assign a preliminary confidence (0-100%) to each. These are rough priors, not final.
4. Identify which hypothesis is most likely given the signal characteristics.
5. Assess how the leading hypothesis would impact the existing investment thesis.

## OUTPUT FORMAT (strict JSON)
{{
  "hypotheses": [
    {{
      "id": "H1",
      "text": "Clear, specific explanation...",
      "confidence": 72,
      "evidence_needed": ["What data would confirm this"]
    }}
  ],
  "leading_hypothesis": "H1",
  "thesis_impact": "How this affects the bull/bear case...",
  "evidence_summary": "What we know vs what we need to verify"
}}

## RULES
- Do NOT invent specific numbers not provided above.
- Do NOT assume access to real-time news — state what you would need to verify.
- Hypotheses must be mutually distinct, not variations of the same idea.
- Consider both fundamental and technical explanations.
"""
