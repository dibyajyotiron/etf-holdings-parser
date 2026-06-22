from etf_holdings_parser.eu import vanguard

SAMPLE_CSV = """Security Name,Ticker,ISIN,Country,Sector,Currency,Asset Type,% of Fund,Shares,Market Value
Apple Inc,AAPL,US0378331005,United States,Technology,USD,Equity,4.50,1000,500000
Microsoft Corp,MSFT,US5949181045,United States,Technology,USD,Equity,4.10,800,400000
"""


def test_parses_basic_rows():
    holdings = vanguard.parse(SAMPLE_CSV)
    assert len(holdings) == 2
    assert holdings[0]["name"] == "Apple Inc"
    assert holdings[0]["weight"] == 4.50
    assert holdings[0]["isin"] == "US0378331005"


def test_skips_comment_rows():
    csv_with_comment = "Security Name,Ticker,ISIN,Country,Sector,Currency,Asset Type,% of Fund,Shares,Market Value\n#footnote,,,,,,,,,\n"
    assert vanguard.parse(csv_with_comment) == []
