from pathlib import Path

from etf_holdings_parser.us import spdr

FIXTURE = Path(__file__).parent / "fixtures" / "spy_holdings_sample.csv"


def test_parses_real_spy_sample():
    """Fixture captured 2026-06-22 from a live download of SSGA's SPY
    holdings xlsx (https://www.ssga.com/.../holdings-daily-us-en-spy.xlsx),
    converted to CSV the same way parser-worker/src/scrapers/us_spdr.py does."""
    raw = FIXTURE.read_text()
    holdings = spdr.parse(raw)

    assert len(holdings) == 20
    top = holdings[0]
    assert top["name"] == "NVIDIA CORP"
    assert top["symbol"] == "NVDA"
    assert top["weight"] == 7.917232
    assert top["shares"] == 291751877.0
    assert top["currency"] == "USD"
    # "Identifier" is CUSIP, not ISIN — must not leak into the isin field.
    assert top["isin"] == ""


def test_skips_rows_without_a_name():
    raw = "Name,Ticker,Identifier,SEDOL,Weight,Sector,Shares Held,Local Currency\n,,,,,,,,\n"
    assert spdr.parse(raw) == []
