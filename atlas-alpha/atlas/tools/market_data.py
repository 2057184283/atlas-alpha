"""
Market Data Tool
================
Abstracts data fetching. V1 uses yfinance for demo.
Future: MCP-compatible adapters for Wind, Bloomberg, etc.
"""

from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf


class MarketDataTool:
    """
    Fetches market data with PIT awareness.

    All methods support `as_of` parameter for backtesting.
    """

    def __init__(self):
        self._cache: dict = {}

    def fetch_stock(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: str = "1y",
        as_of: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch stock price data.

        Args:
            ticker: Yahoo Finance ticker (e.g. "300750.SZ")
            start: Start date string (YYYY-MM-DD)
            end: End date string (YYYY-MM-DD)
            period: yfinance period if start/end not provided
            as_of: PIT truncation date
        """
        cache_key = f"{ticker}_{start}_{end}_{period}"

        if cache_key not in self._cache:
            if start and end:
                df = yf.download(ticker, start=start, end=end, progress=False)
            else:
                df = yf.download(ticker, period=period, progress=False)

            if df.empty:
                raise ValueError(f"No data returned for {ticker}")

            self._cache[cache_key] = df

        df = self._cache[cache_key].copy()

        # Point-in-time truncation
        if as_of is not None:
            df = df[df.index <= as_of]

        return df

    def fetch_sector_index(
        self,
        index_ticker: str = "000941.SS",
        **kwargs
    ) -> pd.DataFrame:
        """Fetch sector/index data."""
        return self.fetch_stock(index_ticker, **kwargs)

    def inject_anomaly(
        self,
        df: pd.DataFrame,
        drop_pct: float = 0.05,
        at_index: int = -1,
    ) -> pd.DataFrame:
        """
        For demo/testing: inject a synthetic price drop.
        This allows us to test the divergence engine without waiting for real crashes.
        """
        df = df.copy()
        col = df.columns[0] if len(df.columns) == 1 else "Close"
        if col not in df.columns:
            col = df.columns[0]

        original = df.iloc[at_index][col]
        df.iloc[at_index, df.columns.get_loc(col)] = original * (1 - drop_pct)
        return df
