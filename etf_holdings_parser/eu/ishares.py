"""Parses iShares UCITS holdings CSV (Ireland/Germany-domiciled ranges).

Ported from portfolio-pal/parser-worker's `_parse_ishares_csv`. iShares CSVs
prepend a metadata block before the real header row; skip down to the row
containing both "Name" and "Weight".
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, csv_rows, safe_float


def parse(raw: str) -> list[Holding]:
    holdings: list[Holding] = []
    for row in csv_rows(raw, skip_until_header_contains=("Name", "Weight")):
        name = row.get("Name", "").strip()
        if not name or name.startswith("-"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=row.get("Ticker", "").strip(),
                isin=row.get("ISIN", "").strip(),
                country=row.get("Location", row.get("Country", "")).strip(),
                sector=row.get("Sector", "").strip(),
                currency=row.get("Currency", "").strip(),
                asset_class=row.get("Asset Class", "").strip(),
                weight=safe_float(row.get("Weight (%)", "0")),
                shares=safe_float(row.get("Shares", "0")),
                market_value=safe_float(row.get("Market Value", "0")),
            )
        )
    return holdings
