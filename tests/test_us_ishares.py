from etf_holdings_parser.us import ishares

SAMPLE_CSV = """Fund Holdings as of,Jun 20 2026,,,,,,,
Fund Name,iShares Core S&P 500 ETF,,,,,,,
Name,Ticker,ISIN,Location,Sector,Currency,Asset Class,Weight (%),Shares,Market Value
Apple Inc,AAPL,US0378331005,United States,Technology,USD,Equity,7.10,1000000,500000000
"""


def test_skips_metadata_header_block():
    holdings = ishares.parse(SAMPLE_CSV)
    assert len(holdings) == 1
    assert holdings[0]["name"] == "Apple Inc"
    assert holdings[0]["weight"] == 7.10


def test_us_delegates_to_eu_module():
    from etf_holdings_parser.eu import ishares as eu_ishares

    assert ishares.parse is eu_ishares.parse
