"""Parses Amundi ETF holdings + profile.

Verified 2026-06-25 via amundietf.co.uk's `/mapi/ProductAPI/getProductsData`
endpoint — a plain JSON POST, **no cookies, no browser session, no
disclaimer gate** at the API level (the disclaimer is page-level JS only).
Both discovery (bulk `productType: "ALL"`) and single-fund holdings
(`productIds: [isin]` + a `composition` block in the request) hit this same
endpoint; the fetcher passes the raw response body straight through here.

Verified against two real funds:
- Amundi Core MSCI World UCITS ETF (IE000CNSFAR2, Direct/Physical
  replication): 1285 real holdings, weights summing to 100.00%, top holdings
  (NVIDIA 5.37%, Apple 4.86%, Microsoft 2.89%) match real MSCI World
  composition.
- Amundi MSCI World Swap UCITS ETF (LU1681043599, Indirect/Swap-Based
  replication): only 125 holdings, all European industrials/financials —
  this is NOT the index look-through, it's the **swap collateral basket**.
  Swap-based ETFs synthesize their index exposure via a total-return swap;
  the "holdings" a swap fund actually owns (and is legally obliged to
  publish) are unrelated collateral securities, not the tracked index's
  constituents. `parse()` still returns this real collateral data (it's not
  fabricated), but `parse_profile()`'s `replication_method` field tells the
  caller which case applies — callers needing true look-through exposure
  for a swap-based fund have no source for that from the issuer at all.
"""

from __future__ import annotations

import json

from etf_holdings_parser.base import FundProfile, Holding

_REPLICATION_MAP = {
    "Direct(Physical)": "Physical (full replication)",
    "Indirect(Swap Based)": "Synthetic (swap-based)",
}

_DOMICILE_TO_ISO = {
    "ireland": "IE",
    "luxembourg": "LU",
    "france": "FR",
    "germany": "DE",
}


def parse(raw: str) -> list[Holding]:
    data = json.loads(raw)
    products = data.get("products") or []
    if not products:
        return []
    composition = products[0].get("composition") or {}
    rows = composition.get("compositionData") or []

    holdings: list[Holding] = []
    for row in rows:
        c = row.get("compositionCharacteristics") or {}
        name = c.get("name")
        if not name:
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=c.get("bbg", ""),
                isin=c.get("isin", ""),
                country=c.get("countryOfRisk", ""),
                sector=c.get("sector", ""),
                currency=c.get("currency", ""),
                asset_class=c.get("type", ""),
                weight=round((row.get("weight") or 0) * 100, 6),
                shares=c.get("quantity") or 0,
                market_value=0,
            )
        )
    return holdings


def parse_profile(raw: str) -> FundProfile:
    data = json.loads(raw)
    products = data.get("products") or []
    if not products:
        return FundProfile()
    p = products[0]
    c = p.get("characteristics") or {}

    profile = FundProfile()
    if isin := c.get("ISIN"):
        profile["isin"] = isin
    if name := c.get("SHARE_MARKETING_NAME"):
        profile["name"] = name
    if ticker := c.get("MNEMO") or c.get("TICKER"):
        profile["ticker"] = ticker
    profile["issuer"] = "Amundi"
    if domicile := c.get("FUND_DOMICILIATION_COUNTRY"):
        profile["domicile"] = _DOMICILE_TO_ISO.get(domicile.strip().lower(), domicile)
    if currency := c.get("CURRENCY"):
        profile["fund_currency"] = currency
    if c.get("FUND_UCITS") is not None:
        profile["ucits"] = bool(c.get("FUND_UCITS"))
    if benchmark := c.get("BENCHMARK_NAME"):
        profile["benchmark_index"] = benchmark
    if replication := c.get("FUND_REPLICATION_METHODOLOGY"):
        profile["replication_method"] = _REPLICATION_MAP.get(replication, replication)
    profile["management_company"] = "Amundi"
    if ter := (c.get("TOTAL_EXPENSE_RATIO") or c.get("TER")):
        profile["ter"] = float(ter)
    if inception := c.get("FIRST_COTATION_DATE") or c.get("LAUNCH_DATE"):
        profile["inception_date"] = str(inception)
    if fund_size := c.get("FUND_AUM_IN_EURO") or c.get("AUM_IN_EURO"):
        profile["fund_size"] = float(fund_size)
        profile["fund_size_currency"] = "EUR"
    if dist := c.get("DISTRIBUTION_POLICY"):
        profile["distribution_policy"] = dist
    if dist_freq := c.get("DISTRIBUTION_FREQUENCY"):
        profile["distribution_frequency"] = dist_freq
    if sfdr := c.get("FUND_SFDR_CLASSIFICATION"):
        profile["sfdr_classification"] = sfdr
    if c.get("CURRENCY_HEDGE") is not None:
        profile["currency_hedged"] = bool(c.get("CURRENCY_HEDGE"))
    composition = p.get("composition") or {}
    if total := composition.get("totalNumberOfInstruments"):
        profile["holdings_count"] = int(total)

    return profile
