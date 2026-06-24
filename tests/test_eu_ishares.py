from pathlib import Path

from etf_holdings_parser.eu import ishares

FIXTURE = Path(__file__).parent / "fixtures" / "igln_overview_sample.xls"


def test_single_asset_etc_returns_synthetic_commodity_holding():
    """IGLN (iShares Physical Gold ETC) holds physical gold bars, not
    securities — its real export (captured 2026-06-23 via a headless
    browser, see parser-worker/src/scrapers/eu_ishares.py) has no Holdings
    worksheet, just Overview/Historical/Performance. This is the trimmed
    Overview sheet only (the real file also has a 2.4MB Historical sheet)."""
    raw = FIXTURE.read_text()
    holdings = ishares.parse(raw)

    assert len(holdings) == 1
    assert holdings[0]["asset_class"] == "Commodity"
    assert holdings[0]["weight"] == 100.0


def test_spreadsheetml_with_no_overview_or_holdings_sheet_returns_empty():
    raw = '<?xml version="1.0"?><ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"></ss:Workbook>'
    assert ishares.parse(raw) == []


def test_parse_profile_extracts_verified_overview_fields():
    raw = FIXTURE.read_text()
    profile = ishares.parse_profile(raw)

    assert profile["isin"] == "IE00B4ND3602"
    assert profile["fund_currency"] == "USD"
    assert profile["domicile"] == "IE"
    assert profile["ucits"] is False
    assert profile["ter"] == 0.12
    assert profile["benchmark_index"] == "LBMA Gold Price"
    assert profile["replication_method"] == "Physical Replication"
    assert profile["inception_date"] == "2011-04-08"
    assert profile["fund_size_currency"] == "USD"
    assert profile["fund_size"] == 34_916_103_605.0


def test_parse_profile_returns_empty_for_holdings_csv_payload():
    """The "_holdings" CSV export has no Overview sheet — parse_profile must
    say "nothing published here", not fabricate or error."""
    raw = "Fund Holdings as of,22-Jun-2026\nName,Weight (%)\nApple Inc,7.1\n"
    assert ishares.parse_profile(raw) == {}
