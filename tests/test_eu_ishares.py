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
