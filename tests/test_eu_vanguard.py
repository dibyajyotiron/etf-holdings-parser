from pathlib import Path

from etf_holdings_parser.eu import vanguard

FIXTURE = Path(__file__).parent / "fixtures" / "vwra_holdings_sample.csv"


def test_parses_real_vwra_sample():
    """Fixture captured 2026-06-23 from a live download of VWRA's "Holdings
    details" xlsx, obtained via a headless browser clicking the real
    Download button on Vanguard's product page (there is no static URL —
    see parser-worker/src/scrapers/eu_vanguard.py), converted to CSV the
    same way the fetcher does."""
    raw = FIXTURE.read_text()
    holdings = vanguard.parse(raw)

    assert len(holdings) == 49  # top 49 real rows in the truncated fixture
    top = holdings[0]
    assert top["name"] == "NVIDIA Corp"
    assert top["symbol"] == "NVDA"
    assert top["weight"] == 4.5995
    assert top["country"] == "US"
    assert top["sector"] == "Technology"
    assert top["market_value"] == 3362450950.8
    assert top["shares"] == 15925220.0


def test_skips_blank_and_disclaimer_rows():
    raw = (
        "Ticker,Holding name,% of market value,Sector,Region,Market value,Shares\n"
        "AAPL,Apple Inc,4.18%,Technology,US,\"US$1,000.00\",100\n"
        ",,,,,,\n"
        "\"Total allocation percentages may not equal 100%...\",,,,,,\n"
    )
    holdings = vanguard.parse(raw)
    assert len(holdings) == 1
    assert holdings[0]["name"] == "Apple Inc"
