from pathlib import Path

from etf_holdings_parser.us import ishares

FIXTURE = Path(__file__).parent / "fixtures" / "cspx_holdings_sample.csv"


def test_parses_real_cspx_sample():
    """Fixture captured 2026-06-23 from a live download of CSPX's holdings
    CSV (iShares Core S&P 500 UCITS ETF), via a headless browser clearing the
    cookie-consent + investor-type gates then GETting the real `.ajax?
    fileType=csv&fileName=CSPX_holdings` link — see
    parser-worker/src/scrapers/eu_ishares.py. Real columns: Ticker, Name,
    Sector, Asset Class, Market Value, Weight (%), Notional Value, Shares,
    Price, Location, Exchange, Market Currency. No ISIN column."""
    raw = FIXTURE.read_text(encoding="utf-8")
    holdings = ishares.parse(raw)

    assert len(holdings) == 26  # truncated fixture: 25 holdings + 1 futures/cash row
    top = holdings[0]
    assert top["name"] == "NVIDIA CORP"
    assert top["symbol"] == "NVDA"
    assert top["weight"] == 7.91
    assert top["sector"] == "Information Technology"
    assert top["country"] == "United States"
    assert top["currency"] == "USD"
    assert top["isin"] == ""  # genuinely absent from this export


def test_skips_trailing_footer_row():
    """The real export ends with a stray non-breaking-space byte that
    DictReader turns into a row of all-None values — must not crash."""
    raw = (
        "Fund Holdings as of,19/Jun/2026\n"
        " \n"
        "Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,Shares,Price,Location,Exchange,Market Currency\n"
        '"AAPL","APPLE INC","Technology","Equity","100.00","7.10","100.00","10.00","10.00","United States","NASDAQ","USD"\n'
        "\xa0"
    )
    holdings = ishares.parse(raw)
    assert len(holdings) == 1
    assert holdings[0]["name"] == "APPLE INC"


def test_us_delegates_to_eu_module():
    from etf_holdings_parser.eu import ishares as eu_ishares

    assert ishares.parse is eu_ishares.parse
