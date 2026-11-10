"""A 'case' is one investigation: a place, a window of years, its monthly record and the scan results."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .climate import Place
from .trends import TrendResult


@dataclass(frozen=True)
class CaseContext:
    """Everything a stage needs to render, passed as one object instead of many globals."""

    place: Place
    start: int
    end: int
    df: pd.DataFrame                    # monthly record, one column per variable code
    results: dict[str, TrendResult]     # scan of every variable over [start, end], with q-values

    @property
    def usable(self) -> dict[str, TrendResult]:
        """Only the variables that could actually be tested here."""
        return {c: r for c, r in self.results.items() if r.usable}

    def window_series(self, code: str) -> pd.Series:
        """The monthly series for ``code`` restricted to the chosen years, without gaps."""
        s = self.df[code].dropna()
        return s[(s.index.year >= self.start) & (s.index.year <= self.end)]
