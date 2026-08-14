#!/usr/bin/env python3
"""
Atlas Alpha — Demo Script
=========================
One command to see the full pipeline:

    python demo.py

What happens:
1. Downloads real market data for CATL (宁德时代) and New Energy Index
2. Injects a synthetic anomaly (simulates a sudden drop)
3. Divergence Engine detects it using statistical Z-score
4. Investigation Agent generates 5 competing hypotheses
5. Reviewer Agent attacks the report
6. Orchestrator maps impact to Thesis Tree
7. Shows final thesis update (with human approval gate)

Requirements:
    pip install -e .
    export OPENAI_API_KEY="sk-..."
"""

import os
import sys

# Check API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ Error: OPENAI_API_KEY not set.")
    print("   export OPENAI_API_KEY='sk-your-key'")
    sys.exit(1)

import pandas as pd
from atlas.tools.market_data import MarketDataTool
from atlas.agents.orchestrator import Orchestrator


def main():
    print("=" * 70)
    print("  ATLAS ALPHA — Autonomous Financial Research System")
    print("  " + "=" * 70)
    print()
    print("  Core principle: LLM reasons. Python calculates. Rules detect.")
    print("  " + "=" * 70)

    # Initialize
    data_tool = MarketDataTool()
    orchestrator = Orchestrator()

    # Step 1: Fetch data
    print("\n📊 [Step 1] Fetching market data...")
    print("      Ticker: 300750.SZ (CATL / 宁德时代)")
    print("      Index:  000941.SS (中证新能)")

    try:
        stock = data_tool.fetch_stock("300750.SZ", period="6mo")
        sector = data_tool.fetch_sector_index("000941.SS", period="6mo")
    except Exception as e:
        print(f"\n⚠️  Yahoo Finance fetch failed: {e}")
        print("   Falling back to synthetic data for demo...")
        stock = create_synthetic_data()
        sector = create_synthetic_data(trend=0.0005)

    print(f"      Stock data:  {len(stock)} days")
    print(f"      Sector data: {len(sector)} days")

    # Step 2: Inject synthetic anomaly
    print("\n🔬 [Step 2] Injecting synthetic anomaly (-5% drop)...")
    stock_anomaly = data_tool.inject_anomaly(stock, drop_pct=0.05, at_index=-1)
    print("      Simulating: CATL drops 5% while sector is flat")

    # Step 3: Run full pipeline
    print("\n🚀 [Step 3] Running Atlas pipeline...")
    print("-" * 70)

    state = orchestrator.run(
        stock_df=stock_anomaly,
        sector_df=sector,
        ticker="CATL",
        skip_human_gate=True,  # Demo mode: auto-approve
    )

    # Step 4: Display results
    print("\n" + "=" * 70)
    print("  INVESTIGATION RESULTS")
    print("=" * 70)

    print(f"\n📋 Run ID: {state.run_id}")
    print(f"📈 Signal: {state.signal.description}")
    print(f"🎯 Severity: {state.signal.severity:.1%}")

    if state.report:
        print(f"\n🔍 Hypotheses Generated:")
        for h in state.report.hypotheses:
            bar = "█" * int(h.confidence / 5) + "░" * (20 - int(h.confidence / 5))
            print(f"   {h.id}: {bar} {h.confidence:>3}% | {h.text[:50]}...")

        print(f"\n⭐ Leading: {state.report.leading_hypothesis}")
        print(f"💡 Thesis Impact: {state.report.thesis_impact}")

    if state.review:
        print(f"\n🛡️  Review Verdict: {state.review.verdict}")
        if state.review.confidence_adjustment:
            print(f"   Confidence adjusted by: {state.review.confidence_adjustment:+.0f}%")

    # Step 5: Show updated thesis
    print("\n" + "=" * 70)
    print("  UPDATED THESIS TREE")
    print("=" * 70)
    tree = orchestrator.thesis.load("CATL")
    print(tree.tree_view())

    print("\n" + "=" * 70)
    print("  ✅ Demo complete.")
    print("  Next: Check data/thesis_catl.json for persisted thesis state.")
    print("=" * 70)


def create_synthetic_data(days: int = 120, trend: float = 0.001, volatility: float = 0.02) -> pd.DataFrame:
    """Create synthetic price data if Yahoo Finance fails."""
    import numpy as np

    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq="B")
    returns = np.random.normal(trend, volatility, days)
    prices = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame({"Close": prices}, index=dates)
    return df


if __name__ == "__main__":
    main()
