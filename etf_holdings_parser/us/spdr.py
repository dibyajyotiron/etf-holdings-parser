"""Parses SPDR/State Street US holdings export (ssga.com daily holdings file).

SPDR's daily holdings export is a flat CSV (no metadata preamble, unlike
iShares) with columns: Name, Ticker, Identifier (SEDOL/ISIN-ish), SEDOL,
Weight, Sector, Shares Held, Local Currency. Column names occasionally vary
slightly by fund (some include "ISIN" instead of "Identifier") — handle both.
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, csv_rows, safe_float


def parse(raw: str) -> list[Holding]:
    holdings: list[Holding] = []
    for row in csv_rows(raw):
        name = (row.get("Name") or row.get("Security Name") or "").strip()
        if not name or name.lower().startswith("total"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=(row.get("Ticker") or "").strip(),
                isin=(row.get("ISIN") or row.get("Identifier") or "").strip(),
                country=(row.get("Country") or "").strip(),
                sector=(row.get("Sector") or row.get("GICS Sector") or "").strip(),
                currency=(row.get("Local Currency") or row.get("Currency") or "").strip(),
                asset_class=(row.get("Asset Class") or "").strip(),
                weight=safe_float(row.get("Weight") or row.get("Weight (%)") or "0"),
                shares=safe_float(row.get("Shares Held") or row.get("Shares") or "0"),
                market_value=safe_float(row.get("Market Value") or "0"),
            )
        )
    return holdings
