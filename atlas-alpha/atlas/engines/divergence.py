"""
Divergence Engine
=================
Core financial logic: detects market anomalies using statistical methods.
ZERO LLM involvement. Every signal is fully auditable.

Design principles:
1. Rolling-window Z-scores, not single-day comparisons
2. Every signal carries raw metrics for audit
3. Point-in-time compatible (as_of parameter)
"""

from typing import Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

from atlas.models import DivergenceSignal, DivergenceType


class DivergenceEngine:
    """
    Detects 6 types of market divergences.

    V1 implements the most critical one: Stock vs Sector.
    Others are scaffolded with clear extension points.
    """

    def __init__(self, lookback_days: int = 30, z_threshold: float = 2.5):
        self.lookback = lookback_days
        self.z_threshold = z_threshold

    def detect_all(
        self,
        stock_df: pd.DataFrame,
        sector_df: pd.DataFrame,
        market_df: Optional[pd.DataFrame] = None,
        as_of: Optional[datetime] = None
    ) -> List[DivergenceSignal]:
        """Run all divergence detectors and return actionable signals."""
        signals = []

        # 1. Stock vs Sector (V1 core)
        sig = self.detect_stock_vs_sector(stock_df, sector_df, as_of)
        if sig and sig.is_actionable():
            signals.append(sig)

        # 2. Stock vs Market (if market data provided)
        if market_df is not None:
            sig = self.detect_stock_vs_market(stock_df, market_df, as_of)
            if sig and sig.is_actionable():
                signals.append(sig)

        # 3-6. Scaffolded for V2
        # sig = self.detect_price_vs_earnings(...)
        # sig = self.detect_price_vs_fundamental(...)

        return sorted(signals, key=lambda x: x.severity, reverse=True)

    def detect_stock_vs_sector(
        self,
        stock_df: pd.DataFrame,
        sector_df: pd.DataFrame,
        as_of: Optional[datetime] = None
    ) -> Optional[DivergenceSignal]:
        """
        Detect when a stock diverges significantly from its sector.

        Method: Rolling relative-return Z-score.
        Not "stock down 5%, sector up 1%" — that's naive.
        We ask: "Is today's relative performance an outlier vs the last N days?"
        """
        # Handle yfinance MultiIndex columns
        stock_df = self._flatten_columns(stock_df)
        sector_df = self._flatten_columns(sector_df)

        # Align and truncate for PIT
        merged = self._prepare_data(stock_df, sector_df, as_of)
        if len(merged) < self.lookback + 5:
            return None

        # Calculate returns
        merged["stock_ret"] = merged["stock"].pct_change()
        merged["sector_ret"] = merged["sector"].pct_change()
        merged["relative"] = merged["stock_ret"] - merged["sector_ret"]

        # Rolling statistics (the core insight)
        merged["rel_mean"] = merged["relative"].rolling(window=self.lookback, min_periods=self.lookback).mean()
        merged["rel_std"] = merged["relative"].rolling(window=self.lookback, min_periods=self.lookback).std()
        merged["z_score"] = (merged["relative"] - merged["rel_mean"]) / merged["rel_std"]

        # Latest observation
        latest = merged.iloc[-1]
        z = latest["z_score"]

        if pd.isna(z) or abs(z) < self.z_threshold:
            return None

        # Severity: 2.5 sigma → 60%, 4.0 sigma → 100%
        severity = min(abs(z) / 4.0, 1.0)

        ticker_name = getattr(stock_df, "name", "Unknown")
        if isinstance(ticker_name, pd.MultiIndex):
            ticker_name = "Stock"

        return DivergenceSignal(
            ticker=ticker_name if isinstance(ticker_name, str) else "Stock",
            date=pd.Timestamp(merged.index[-1]).to_pydatetime(),
            divergence_type=DivergenceType.STOCK_VS_SECTOR,
            severity=severity,
            z_score=float(z),
            stock_return=float(latest["stock_ret"] * 100),
            sector_return=float(latest["sector_ret"] * 100),
            description=(
                f"Stock {latest['stock_ret']*100:+.1f}% vs Sector {latest['sector_ret']*100:+.1f}% | "
                f"Relative Z-score: {z:+.2f} (lookback={self.lookback}d)"
            ),
            metrics={
                "lookback_days": self.lookback,
                "rolling_mean_relative": float(latest["rel_mean"]),
                "rolling_std_relative": float(latest["rel_std"]),
                "absolute_stock_return": float(latest["stock_ret"]),
                "absolute_sector_return": float(latest["sector_ret"]),
                "data_points": len(merged),
            }
        )

    def detect_stock_vs_market(
        self,
        stock_df: pd.DataFrame,
        market_df: pd.DataFrame,
        as_of: Optional[datetime] = None
    ) -> Optional[DivergenceSignal]:
        """Same logic as sector, but against broad market index."""
        stock_df = self._flatten_columns(stock_df)
        market_df = self._flatten_columns(market_df, col_name="market")

        merged = self._prepare_data(stock_df, market_df, as_of, right_col="market")
        if len(merged) < self.lookback + 5:
            return None

        merged["stock_ret"] = merged["stock"].pct_change()
        merged["market_ret"] = merged["market"].pct_change()
        merged["relative"] = merged["stock_ret"] - merged["market_ret"]

        merged["rel_mean"] = merged["relative"].rolling(window=self.lookback, min_periods=self.lookback).mean()
        merged["rel_std"] = merged["relative"].rolling(window=self.lookback, min_periods=self.lookback).std()
        merged["z_score"] = (merged["relative"] - merged["rel_mean"]) / merged["rel_std"]

        latest = merged.iloc[-1]
        z = latest["z_score"]

        if pd.isna(z) or abs(z) < self.z_threshold:
            return None

        severity = min(abs(z) / 4.0, 1.0)

        return DivergenceSignal(
            ticker="Stock",
            date=pd.Timestamp(merged.index[-1]).to_pydatetime(),
            divergence_type=DivergenceType.STOCK_VS_MARKET,
            severity=severity,
            z_score=float(z),
            stock_return=float(latest["stock_ret"] * 100),
            sector_return=float(latest["market_ret"] * 100),
            description=(
                f"Stock {latest['stock_ret']*100:+.1f}% vs Market {latest['market_ret']*100:+.1f}% | "
                f"Relative Z-score: {z:+.2f}"
            ),
            metrics={
                "lookback_days": self.lookback,
                "rolling_mean_relative": float(latest["rel_mean"]),
                "rolling_std_relative": float(latest["rel_std"]),
            }
        )

    def _flatten_columns(self, df: pd.DataFrame, col_name: str = "Close") -> pd.DataFrame:
        """Handle yfinance MultiIndex columns."""
        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            # Try to find the requested column at level 0
            if col_name in df.columns.get_level_values(0):
                df = df[col_name].copy()
                if isinstance(df, pd.DataFrame) and isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                elif isinstance(df, pd.Series):
                    df = df.to_frame(name=col_name)
            else:
                # Fallback: take first column
                first_col = df.columns[0]
                df = df[first_col].to_frame(name=col_name)
        else:
            if col_name not in df.columns and "Close" in df.columns:
                df = df[["Close"]].rename(columns={"Close": col_name})
            elif col_name in df.columns:
                df = df[[col_name]]
        return df

    def _prepare_data(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        as_of: Optional[datetime],
        left_col: str = "stock",
        right_col: str = "sector"
    ) -> pd.DataFrame:
        """Merge two price series and apply PIT truncation."""
        left_df = left_df.copy()
        right_df = right_df.copy()

        # Rename for clarity
        left_df.columns = [left_col]
        right_df.columns = [right_col]

        # Merge on date index
        merged = pd.merge(left_df, right_df, left_index=True, right_index=True, how="inner")
        merged = merged.dropna()

        # Point-in-time truncation
        if as_of is not None:
            merged = merged[merged.index <= as_of]

        return merged
