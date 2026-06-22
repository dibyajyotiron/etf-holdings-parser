"""Parses Vanguard's Ireland/Europe UCITS holdings export (fund-facts CSV).

Ported from portfolio-pal/parser-worker's `_parse_vanguard_csv` — same format,
just with the HTTP fetch removed (caller fetches the CSV text and passes it in).
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, csv_rows, safe_float


def parse(raw: str) -> list[Holding]:
    holdings: list[Holding] = []
    for row in csv_rows(raw):
        name = row.get("Security Name", row.get("Name", ""))
        if not name or name.startswith("#"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=row.get("Ticker", row.get("Symbol", "")),
                isin=row.get("ISIN", ""),
                country=row.get("Country", ""),
                sector=row.get("Sector", ""),
                currency=row.get("Currency", ""),
                asset_class=row.get("Asset Type", ""),
                weight=safe_float(row.get("% of Fund", row.get("Weight (%)", "0"))),
                shares=safe_float(row.get("Shares", "0")),
                market_value=safe_float(row.get("Market Value", "0")),
            )
        )
    return holdings
