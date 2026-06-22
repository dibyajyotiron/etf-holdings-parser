"""Normalizes an edgartools N-PORT holdings collection into the common shape.

Ported from portfolio-pal/parser-worker's `_try_sec_nport` — that function did
both the edgartools fetch *and* the normalization; here we only keep the
normalization half. The caller is responsible for getting `holdings_data`
(the iterable edgartools returns from `filing.holdings`).
"""

from __future__ import annotations

from typing import Iterable

from etf_holdings_parser.base import Holding


def parse(holdings_data: Iterable) -> list[Holding]:
    out: list[Holding] = []
    for h in holdings_data:
        weight = getattr(h, "pct_val", None)
        out.append(
            Holding(
                name=str(getattr(h, "name", "")),
                symbol=str(getattr(h, "ticker", "")),
                isin=str(getattr(h, "isin", "")),
                country=str(getattr(h, "investment_country", "")),
                sector="",
                currency=str(getattr(h, "currency_code", "")),
                asset_class=str(getattr(h, "asset_category", "")),
                weight=float(weight) if weight is not None else 0.0,
                shares=float(getattr(h, "quantity", 0) or 0),
                market_value=float(getattr(h, "valuation_usd", 0) or 0),
            )
        )
    return out
