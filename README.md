# etf-holdings-parser

Pure parsing logic for ETF data: per-constituent holdings exports (CSV/XML)
**and** fund-level profile data (TER, AUM, NAV, replication method, tracking
difference, distributions, allocation breakdowns, cost-impact metrics, etc.),
normalized to two common record shapes.

This package does **no network I/O**. It is not a service and exposes no
HTTP API — it's a library. Callers (e.g. a scraper that knows each issuer's
URL pattern) fetch the raw text and pass it in; modules here only parse and
compute. This README documents it like an API anyway — "request" below
means "what you pass into a function," "response" means "what you get back"
— since that's the contract that matters to a caller.

## Why two shapes, not one

- **`Holding`** is one row inside the fund — one stock/bond it owns. It is
  inherently narrow: a single position only ever has a name, a weight, a
  country, a sector, and a few other facts. Don't expect 500 fields here —
  that's not what a holding _is_.
- **`FundProfile`** is the fund itself — the "factsheet" half of ETF data.
  This is where the richness lives: cost, structure, risk, performance,
  every allocation breakdown, and computed cost-impact metrics. This is the
  shape that needs to be a complete justETF replacement (superset of every
  field justETF shows today) plus whatever extra the issuer publishes.

If you only look at `Holding` and conclude "this only has 10 fields," that's
expected — go look at `FundProfile` for the other ~70 fields, multiplied by
however many holdings/allocation rows/calendar years a given fund has data
for (which is where "500 data points for one ETF" actually comes from once
you flatten everything out).

## Install

```bash
pip install etf-holdings-parser
```

(Not yet on PyPI as of this writing — install from GitHub in the meantime:
`pip install git+https://github.com/dibyajyotiron/etf-holdings-parser.git`.)

## API Reference

### 1. Holdings parsers — `parse(raw: str) -> list[Holding]`

**Request** (what you pass in): the raw CSV/XML text of one issuer's
holdings export, exactly as downloaded — no preprocessing needed, each
module handles its issuer's quirks (metadata header blocks, percent signs,
thousands separators, etc.).

```python
from etf_holdings_parser.eu import vanguard

raw_csv = open("vanguard_vwra_holdings.csv").read()
holdings = vanguard.parse(raw_csv)
```

**Response** (what you get back): a `list[Holding]`, one dict per
constituent:

```jsonc
[
  {
    "name": "Apple Inc",
    "symbol": "AAPL",
    "isin": "US0378331005",
    "country": "United States",
    "sector": "Technology",
    "currency": "USD",
    "asset_class": "Equity",
    "weight": 4.5, // percent, 0-100
    "shares": 1000,
    "market_value": 500000,
  },
]
```

| Field          | Type  | Notes                                                             |
| -------------- | ----- | ----------------------------------------------------------------- |
| `name`         | str   | Security name as the issuer reports it                            |
| `symbol`       | str   | Ticker, when the issuer provides one                              |
| `isin`         | str   |                                                                   |
| `country`      | str   | Full country name (not ISO code) — matches issuer convention      |
| `sector`       | str   | Issuer's own sector taxonomy (GICS-like, not always GICS exactly) |
| `currency`     | str   | Trading currency of the holding                                   |
| `asset_class`  | str   | "Equity", "Fixed Income", "Cash", "Derivative", etc.              |
| `weight`       | float | Percent of fund, 0–100 (not 0–1)                                  |
| `shares`       | float |                                                                   |
| `market_value` | float | In the fund's base currency unless the issuer says otherwise      |

Resolve which parser to call dynamically instead of importing directly:

```python
from etf_holdings_parser import get_parser, NotImplementedParser

try:
    parse = get_parser("eu", "vanguard")
    holdings = parse(raw_csv)
except KeyError:
    ...  # (region, issuer) pair not registered at all
except NotImplementedParser:
    ...  # registered, but real format not ported yet — see Status below
```

`list_parsers() -> list[tuple[str, str, bool]]` returns every registered
`(region, issuer, implemented)` triple, e.g. `("eu", "vanguard", True)`.

### 2. Fund profile — `FundProfile` (schema, not yet auto-populated from raw text)

`FundProfile` (in `etf_holdings_parser.base`) is a `TypedDict` covering:

- **Identity**: `isin`, `name`, `ticker`, `issuer`, `domicile`, `fund_currency`, `legal_structure`, `ucits`, `benchmark_index`, `index_provider`, `investment_focus`, `asset_class`, `inception_date`, `management_company`, `depositary`, `description`
- **Costs**: `ter`, `management_fee`, `other_costs`, `avg_bid_ask_spread`, `tracking_difference_1y`, `tracking_error_1y`, `securities_lending`, `securities_lending_revenue_share_to_fund`
- **Size / structure**: `fund_size`, `fund_size_currency`, `nav_per_share`, `nav_currency`, `holdings_count`, `replication_method`, `swap_counterparties`, `distribution_policy`, `distribution_frequency`, `last_distribution_amount`, `last_distribution_date`, `distribution_yield_ttm`, `currency_hedged`, `hedged_share_class_isins`, `use_of_derivatives`, `leverage_factor`, `rebalance_frequency`
- **Listings**: `exchanges` (list of `ExchangeListing`: `exchange`, `ticker`, `currency`, `bloomberg_ticker`, `reuters_ric`, `trading_currency`)
- **Risk / regulatory**: `srri`, `sfdr_classification`, `sustainability`, `kiid_url`, `factsheet_url`
- **Fixed-income-specific**: `duration`, `yield_to_maturity`, `credit_quality_allocation`, `maturity_allocation`
- **Performance**: `return_1m`, `return_3m`, `return_ytd`, `return_1y`, `return_3y_annualized`, `return_5y_annualized`, `return_since_inception_annualized`, `calendar_returns` (list of `CalendarReturn`: `year`, `return_pct`), `volatility_1y`, `volatility_3y`, `max_drawdown`, `sharpe_ratio`, `sortino_ratio`
- **Allocation breakdowns** (each a `list[AllocationBucket]` of `{label, weight}`): `sector_allocation`, `country_allocation`, `region_allocation`, `currency_allocation`, `asset_class_allocation`, `market_cap_allocation`, plus `top_10_concentration` (float)
- **Computed cost-impact**: `fee_drag_10y_on_amount`, `fee_drag_amount`

No issuer populates every field — a bond ETF has `duration`/`yield_to_maturity`,
an equity ETF doesn't; some issuers disclose `tracking_difference_1y`, others
don't. **Leave a key absent rather than guessing a value.**

`FundProfile` is a schema, not yet wired to real per-issuer factsheet
parsers (those need real sample pages — see "Capturing new issuer formats"
below). It exists so downstream consumers (e.g. the Go backend / screener
this package feeds) can design against the full target shape now, and so
contributors know exactly what a new factsheet parser should populate.

### 3. Cost-impact calculator — `fee_drag(...)`

The one thing no provider hands you directly but every investor needs: what
does this ETF's expense ratio actually cost in absolute terms?

```python
from etf_holdings_parser import fee_drag

fee_drag(principal=10000, annual_ter_pct=0.20, years=10)
```

**Response:**

```jsonc
{
  "years": [1, 2, 3, ..., 10],
  "with_fee":    [9980.0, 9960.04, ...],   // compounds with TER drag applied
  "without_fee": [10000.0, 10000.0, ...],  // same growth assumption, no fee
  "total_fee_drag": 199.0                   // absolute cost over the period
}
```

By default `annual_growth_pct=0`, which isolates the fee's drag from market
returns — "what this ETF costs you no matter what the market does," the
number that's comparable across funds regardless of their backtested
performance. Pass `annual_growth_pct=7.0` (or your own assumption) to see
the cost net of compounding growth instead.

```python
fee_drag(principal=10000, annual_ter_pct=0.07, years=20, annual_growth_pct=7.0)["total_fee_drag"]
# vs.
fee_drag(principal=10000, annual_ter_pct=0.75, years=20, annual_growth_pct=7.0)["total_fee_drag"]
```

## Layout

```
etf_holdings_parser/
  base.py        # Holding, FundProfile, AllocationBucket, ExchangeListing,
                  # CalendarReturn schemas + fee_drag() + the parser registry
  us/*.py         # one holdings-parser module per US issuer
  eu/*.py         # one holdings-parser module per EU-domiciled issuer
                  # (Ireland, Luxembourg, Germany, France, ...)
  sec_nport.py    # normalizes an edgartools N-PORT holdings object
```

## Status

Two different things can be true independently of each other, and the
distinction matters: **(a)** does `parse(raw_text)` correctly turn a given
issuer's export into `Holding` records, and **(b)** can the *caller*
(`parser-worker`, which owns network I/O — this package never makes a
request) actually fetch that export over plain HTTPS right now. An issuer
can pass (a) and fail (b), e.g. because the endpoint is hidden behind a bot
challenge that only a real browser session clears.

**Parser logic implemented (a) and live-fetch verified (b)** — confirmed
end-to-end against a real download, not just a hand-built fixture:
- `us.spdr` (SPY, 2026-06-22) — `parser-worker/src/scrapers/us_spdr.py`
  fetch + this parser, 512 real holdings parsed via plain HTTPS GET.
- `eu.vanguard` (VWRA, 2026-06-23) — `parser-worker/src/scrapers/eu_vanguard.py`
  drives a real headless browser to click the fund page's actual "Holdings
  details" Download button (there is no static URL; the old guessed
  `fund-facts-{id}.csv` path never existed). 3771 real holdings parsed.
- `eu.ishares` (IGLN, 2026-06-23) — `parser-worker/src/scrapers/eu_ishares.py`
  drives a headless browser through a cookie-consent banner and an
  investor-type/country gate (both required before the real `.ajax`
  download link even appears in the DOM), then fetches it authenticated.
  Real format is SpreadsheetML XML, not the guessed CSV. IGLN itself is a
  single-asset physical-gold ETC with no holdings list — `parse()` returns
  one synthetic 100%-weighted "Commodity" holding for that case; an equity
  UCITS fund's actual Holdings-worksheet format is still unverified (see
  `_parse_holdings_sheet`'s docstring in `eu/ishares.py`).
- `us.ishares` delegates to `eu.ishares` (same underlying BlackRock format),
  but no US iShares fund has been independently live-verified yet.

**Why a headless browser, not just `requests`**: both Vanguard and iShares'
download links are added to the page by client-side JS — Vanguard's because
the file is generated as an in-browser blob (no server-side file exists at
any URL), iShares' because the link is hidden behind gates whose state
(cookies) only exists after a real page renders. `parser-worker/src/scrapers/browser.py`
holds the shared Playwright helper both fetchers use.

**Parser logic implemented (a), live-fetch unverified (b)**:
- `sec_nport` — implemented against edgartools' object shape; not
  independently re-verified against a live SEC filing in the same pass.

**Stubbed** (registered, raise `NotImplementedParser` until ported — neither
(a) nor (b) done yet): `eu.xtrackers`, `eu.amundi`, `eu.spdr`, `eu.invesco`,
`eu.ubs`, `eu.hsbc`, `eu.wisdomtree`, `eu.lng`, `eu.vaneck`, `eu.bnpparibas`,
`eu.fidelity`, `eu.jpmorgan`, `eu.franklintempleton`, `eu.deka`,
`eu.goldmansachs`, `us.vanguard`, `us.invesco`, `us.schwab`, `us.jpmorgan`,
`us.fidelity`, `us.dimensional`, `us.firsttrust`, `us.wisdomtree`.

**Fund profile parsers**: not yet implemented for any issuer as structured
`FundProfile` output — `FundProfile` is currently a schema only (see above),
though `eu.ishares`'s `_overview_key_values()` helper already extracts
TER/AUM/domicile/replication-style data from the real iShares Overview
sheet internally (just not yet mapped out to a public `FundProfile` return).

**Extending to a new fund**: for issuers already covered (Vanguard EU,
iShares EU), adding a fund is just adding its ISIN + product page URL to
`parser-worker/src/scrapers/funds.py` — no new parser code needed unless the
fund's export shape differs (e.g. an equity iShares fund's real Holdings
worksheet, once someone captures one).

## Capturing new issuer formats (contributions welcome)

Each stubbed module's docstring has a TODO. To turn a stub into a real
parser:

1. Visit the issuer's fund-finder page, find the specific fund (by ISIN or
   ticker), and grab:
   - The **holdings download** (usually a "Holdings" tab → CSV/XLSX export)
   - The **factsheet/KIID/PRIIPs document** (usually a "Literature"/"Documents"
     tab → PDF) — this is where most `FundProfile` fields come from
2. Save the raw file(s) and open an issue or PR with a sample attached (or
   paste the raw text/structure).
3. Add a fixture under `tests/` using the real (or anonymized) sample, then
   port the column mapping into the stub following the pattern in
   `eu/vanguard.py` or `eu/ishares.py`.

Fund-finder / holdings-download starting points by issuer (these are
fund-finder _root_ pages — each fund's actual export URL is fund-specific,
found via the fund's own page):

**US issuers**
| Issuer | Fund finder | Look for |
|---|---|---|
| iShares (BlackRock) | https://www.ishares.com/us/products/etf-investments | "Holdings" tab → download |
| Vanguard | https://investor.vanguard.com/investment-products/etfs | "Portfolio & Management" → holdings |
| SPDR (State Street) | https://www.ssga.com/us/en/intermediary/etfs/fund-finder | "Holdings" tab |
| Invesco | https://www.invesco.com/us/financial-products/etfs/list | "Fund Holdings" tab |
| Charles Schwab | https://www.schwabassetmanagement.com/products | ETF page → Holdings |
| JPMorgan | https://am.jpmorgan.com/us/en/asset-management/per/products/etf | Fund page |
| Fidelity | https://www.fidelity.com/etfs/overview | Fund page → Holdings |
| Dimensional | https://www.dimensional.com/us-en/funds | Fund page |
| First Trust | https://www.ftportfolios.com/Retail/Etf/EtfFunds.aspx | Fund page → Holdings |
| WisdomTree | https://www.wisdomtree.com/investments/etfs | Fund page → Holdings |

**EU-domiciled issuers**
| Issuer | Fund finder | Look for |
|---|---|---|
| iShares (BlackRock) Europe | https://www.ishares.com/uk/individual/en/products/etf-investing | "Holdings" tab |
| Xtrackers (DWS) | https://etf.dws.com/en-gb/ | Fund page → Composition |
| Amundi (incl. ex-Lyxor) | https://www.amundietf.com/en/professional/product | Documents → Composition |
| SPDR Europe | https://www.ssga.com/uk/en_gb/intermediary/etfs/fund-finder | "Holdings" tab |
| Vanguard Europe | https://www.vanguard.co.uk/professional/product/etf | Fund documents |
| Invesco Europe | https://www.invesco.com/uk/en/financial-products/etfs.html | Fund page |
| UBS ETF | https://www.ubs.com/global/en/assetmanagement/etf.html | Fund page → Holdings |
| HSBC ETF | https://www.etf.hsbc.com/ | Fund page |
| WisdomTree Europe | https://www.wisdomtree.eu/en-gb/etfs | Fund page → Holdings |
| L&G (Legal & General) | https://www.lgimetf.com/ | Fund page |
| VanEck Europe | https://www.vaneck.com/europe/en/ucits-etfs/ | Fund page |
| BNP Paribas Easy | https://www.bnpparibas-am.com/en-int/easy-etf/ | Fund page |
| Franklin Templeton | https://www.franklintempleton.com/investments/options/exchange-traded-funds | Fund page |
| Deka | https://etf.deka.de/ | Fund page |
| Goldman Sachs ETFs | https://www.gsam.com/content/gsam/us/en/advisors/etfs.html | Fund page |

If you grab a sample for a fund you actually hold, that's the fastest path
to a real parser — open an issue with the raw export attached.
