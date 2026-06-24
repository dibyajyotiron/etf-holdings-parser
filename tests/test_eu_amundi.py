from pathlib import Path

from etf_holdings_parser.eu import amundi

PHYSICAL_FIXTURE = Path(__file__).parent / "fixtures" / "amundi_core_msci_world_physical_sample.json"
SWAP_FIXTURE = Path(__file__).parent / "fixtures" / "amundi_msci_world_swap_sample.json"


def test_physical_fund_returns_real_index_holdings():
    """Amundi Core MSCI World (IE000CNSFAR2, Direct/Physical replication) —
    captured 2026-06-25 via a plain JSON POST to amundietf.co.uk's
    ProductAPI, no browser/cookies needed. Trimmed to the top 15 of 1285
    real holdings for fixture size; full file verified live (weights summed
    to 100.00% across all 1285 rows, top holding NVIDIA at 5.37%)."""
    raw = PHYSICAL_FIXTURE.read_text()
    holdings = amundi.parse(raw)

    assert len(holdings) == 15
    assert holdings[0]["name"] == "NVIDIA CORP"
    assert holdings[0]["isin"] == "US67066G1040"
    assert holdings[0]["country"] == "United States"
    assert round(holdings[0]["weight"], 2) == 5.37


def test_swap_fund_returns_collateral_basket_not_index_lookthrough():
    """Amundi MSCI World Swap (LU1681043599, Indirect/Swap-Based) publishes
    its swap collateral basket as "composition" — real holdings, but NOT
    representative of the tracked index (the live fund had only 124 real
    holdings total, all European industrials/financials, despite tracking a
    global index). parse_profile()'s replication_method is how a caller
    detects this case."""
    raw = SWAP_FIXTURE.read_text()
    holdings = amundi.parse(raw)
    profile = amundi.parse_profile(raw)

    assert len(holdings) == 15
    assert profile["replication_method"] == "Synthetic (swap-based)"


def test_parse_profile_physical_fund():
    raw = PHYSICAL_FIXTURE.read_text()
    profile = amundi.parse_profile(raw)

    assert profile["isin"] == "IE000CNSFAR2"
    assert profile["domicile"] == "IE"
    assert profile["replication_method"] == "Physical (full replication)"
    assert profile["ter"] == 0.12
    assert profile["holdings_count"] == 1285
    assert profile["fund_size_currency"] == "EUR"


def test_parse_profile_swap_fund_ticker_and_domicile():
    raw = SWAP_FIXTURE.read_text()
    profile = amundi.parse_profile(raw)

    assert profile["ticker"] == "CW8"
    assert profile["domicile"] == "LU"
    assert profile["ter"] == 0.38


def test_parse_returns_empty_for_no_products():
    assert amundi.parse('{"products": []}') == []
    assert amundi.parse_profile('{"products": []}') == {}
