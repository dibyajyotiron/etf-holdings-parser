"""Parses Vanguard's Ireland/Europe UCITS "Holdings details" export.

Verified 2026-06-23 against a live download of VWRA's holdings xlsx
(captured via a headless browser clicking the real "Download" button on
https://www.vanguard.co.uk/professional/product/etf/equity/9679/... — the
file is NOT available at a static URL; see
parser-worker/src/scrapers/eu_vanguard.py for the browser-driven fetch).

Real columns observed: Ticker, Holding name, % of market value, Sector,
Region, Market value, Shares. There is no ISIN or Currency column. Vanguard's
"Region" column is actually a 2-letter ISO country code (e.g. "DE", "RU"),
not a macro-region — mapped to `country` here; this package's caller derives
a macro-region from that via the geo package, not from Vanguard's own label.

The header is preceded by ~6 metadata rows (download date, fund name, "as at"
date) and followed by blank rows + a multi-line disclaimer — both handled by
`csv_rows`' header-detection and the name/Ticker emptiness check below.
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, csv_rows, safe_float


def parse(raw: str) -> list[Holding]:
    holdings: list[Holding] = []
    for row in csv_rows(raw, skip_until_header_contains=("Ticker", "Holding name")):
        name = (row.get("Holding name") or "").strip()
        ticker = (row.get("Ticker") or "").strip()
        if not name or not ticker:
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=ticker,
                isin="",
                country=(row.get("Region") or "").strip(),
                sector=(row.get("Sector") or "").strip(),
                currency="",
                asset_class="Equity",
                weight=safe_float(row.get("% of market value") or "0"),
                shares=safe_float(row.get("Shares") or "0"),
                market_value=safe_float(row.get("Market value") or "0"),
            )
        )
    return holdings
