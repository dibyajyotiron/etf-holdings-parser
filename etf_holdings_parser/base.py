"""Shared types and helpers for issuer holdings parsers."""

from __future__ import annotations

import csv
import importlib
import io
from typing import TypedDict


class Holding(TypedDict, total=False):
    """One constituent row inside an ETF. Inherently narrow — it's a single
    position, not the fund itself. Fund-level richness lives in FundProfile."""

    name: str
    symbol: str
    isin: str
    country: str
    sector: str
    currency: str
    asset_class: str
    weight: float
    shares: float
    market_value: float


class AllocationBucket(TypedDict, total=False):
    """One row of an allocation breakdown (sector/country/currency/region/
    market-cap/asset-class/credit-quality/maturity-bucket, etc.)."""

    label: str
    weight: float  # percent, 0-100


class ExchangeListing(TypedDict, total=False):
    """One cross-listing of the same fund on a different exchange — issuers
    commonly list the same ISIN under different tickers/currencies/MICs."""

    exchange: str
    ticker: str
    currency: str
    bloomberg_ticker: str
    reuters_ric: str
    trading_currency: str


class CalendarReturn(TypedDict, total=False):
    """One calendar year's total return."""

    year: int
    return_pct: float


class FundProfile(TypedDict, total=False):
    """Fund-level metadata — the "factsheet" half of an ETF's data, as
    opposed to its constituent holdings. This is deliberately wide: it's the
    superset of what justETF shows today (so this package can fully replace
    it) plus fields issuers publish that justETF doesn't surface, plus a
    couple of computed cost metrics (fee_drag_*) that no provider gives you
    directly but every investor making a decision actually needs.

    No single issuer populates every field — bond ETFs have duration/YTM,
    equity ETFs don't; some issuers publish tracking difference, others
    don't. Leave a field unset (key absent) rather than guessing a value.
    """

    # --- Identity ---
    isin: str
    name: str
    ticker: str
    issuer: str  # e.g. "iShares", "Vanguard"
    domicile: str  # ISO country code, e.g. "IE", "LU", "US"
    fund_currency: str  # base/accounting currency
    legal_structure: str  # "UCITS" | "40 Act ETF" | "ETC" | ...
    ucits: bool
    benchmark_index: str
    index_provider: str  # e.g. "MSCI", "FTSE Russell", "Solactive"
    investment_focus: str  # e.g. "Equity, World"
    asset_class: str  # "Equity" | "Fixed Income" | "Commodity" | "Multi-Asset" | ...
    inception_date: str  # ISO date
    management_company: str
    depositary: str
    description: str

    # --- Costs (the part that actually changes outcomes) ---
    ter: float  # total expense ratio, percent
    management_fee: float  # percent, subset of TER where issuer breaks it out
    other_costs: float  # percent, TER minus management fee where disclosed
    avg_bid_ask_spread: float  # percent
    tracking_difference_1y: float  # percent; negative = underperformed benchmark
    tracking_error_1y: float  # percent, annualized stdev of tracking difference
    securities_lending: bool
    securities_lending_revenue_share_to_fund: float  # percent

    # --- Size / structure ---
    fund_size: float
    fund_size_currency: str
    nav_per_share: float
    nav_currency: str
    holdings_count: int
    replication_method: str  # "Physical (full replication)" | "Physical (optimized sampling)" | "Synthetic (swap-based)"
    swap_counterparties: list[str]
    distribution_policy: str  # "Accumulating" | "Distributing"
    distribution_frequency: str  # "Annual" | "Quarterly" | "Monthly" | "-"
    last_distribution_amount: float
    last_distribution_date: str
    distribution_yield_ttm: float  # percent
    currency_hedged: bool
    hedged_share_class_isins: list[str]
    use_of_derivatives: bool
    leverage_factor: float  # e.g. 2.0 for a 2x leveraged ETF
    rebalance_frequency: str  # "Quarterly" | "Semi-annual" | ...

    # --- Listings ---
    exchanges: list[ExchangeListing]

    # --- Risk / regulatory ---
    srri: int  # SRRI 1-7 risk indicator from KIID/PRIIPs
    sfdr_classification: str  # "Article 6" | "Article 8" | "Article 9"
    sustainability: bool
    kiid_url: str
    factsheet_url: str

    # --- Fixed-income-specific (absent for equity ETFs) ---
    duration: float  # years
    yield_to_maturity: float  # percent
    credit_quality_allocation: list[AllocationBucket]
    maturity_allocation: list[AllocationBucket]

    # --- Performance (computed by us elsewhere from candle history, but
    # included here so a screener can render one unified fund record) ---
    return_1m: float
    return_3m: float
    return_ytd: float
    return_1y: float
    return_3y_annualized: float
    return_5y_annualized: float
    return_since_inception_annualized: float
    calendar_returns: list[CalendarReturn]
    volatility_1y: float
    volatility_3y: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float

    # --- Allocation breakdowns (one bucket list per dimension) ---
    sector_allocation: list[AllocationBucket]
    country_allocation: list[AllocationBucket]
    region_allocation: list[AllocationBucket]
    currency_allocation: list[AllocationBucket]
    asset_class_allocation: list[AllocationBucket]
    market_cap_allocation: list[AllocationBucket]
    top_10_concentration: float  # percent, sum of top 10 holdings' weight

    # --- Computed cost-impact metrics (not from any provider — see fee_drag) ---
    fee_drag_10y_on_amount: float  # cumulative cost in `fee_drag_amount`'s currency
    fee_drag_amount: float  # the principal the above was computed on, e.g. 10000


class NotImplementedParser(NotImplementedError):
    """Raised by a stub module whose real CSV/XML format hasn't been ported yet."""


def safe_float(value: str | None) -> float:
    if not value:
        return 0.0
    cleaned = str(value).strip()
    for symbol in ("US$", "$", "£", "€", ",", "%"):
        cleaned = cleaned.replace(symbol, "")
    try:
        return float(cleaned.strip())
    except ValueError:
        return 0.0


def csv_rows(text: str, skip_until_header_contains: tuple[str, ...] = ()) -> list[dict]:
    """DictReader over `text`, optionally skipping a leading metadata block.

    Some issuer exports (e.g. iShares) prepend a few lines of fund metadata
    before the actual header row. `skip_until_header_contains` lets a caller
    say "skip lines until one contains all of these substrings".
    """
    lines = text.splitlines()
    start = 0
    if skip_until_header_contains:
        for i, line in enumerate(lines):
            if all(token in line for token in skip_until_header_contains):
                start = i
                break
    return list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))


# (region, issuer) -> dotted module path. "implemented" tracks whether `parse`
# does real work or just raises NotImplementedParser — keep this in sync with
# each module's docstring.
REGISTRY: dict[tuple[str, str], dict[str, object]] = {
    ("eu", "vanguard"): {"module": "etf_holdings_parser.eu.vanguard", "implemented": True},
    ("eu", "ishares"): {"module": "etf_holdings_parser.eu.ishares", "implemented": True},
    ("eu", "xtrackers"): {"module": "etf_holdings_parser.eu.xtrackers", "implemented": False},
    ("eu", "amundi"): {"module": "etf_holdings_parser.eu.amundi", "implemented": True},
    ("eu", "spdr"): {"module": "etf_holdings_parser.eu.spdr", "implemented": False},
    ("eu", "invesco"): {"module": "etf_holdings_parser.eu.invesco", "implemented": False},
    ("eu", "ubs"): {"module": "etf_holdings_parser.eu.ubs", "implemented": False},
    ("eu", "hsbc"): {"module": "etf_holdings_parser.eu.hsbc", "implemented": False},
    ("eu", "wisdomtree"): {"module": "etf_holdings_parser.eu.wisdomtree", "implemented": False},
    ("eu", "lng"): {"module": "etf_holdings_parser.eu.lng", "implemented": False},
    ("eu", "vaneck"): {"module": "etf_holdings_parser.eu.vaneck", "implemented": False},
    ("eu", "bnpparibas"): {"module": "etf_holdings_parser.eu.bnpparibas", "implemented": False},
    ("eu", "fidelity"): {"module": "etf_holdings_parser.eu.fidelity", "implemented": False},
    ("eu", "jpmorgan"): {"module": "etf_holdings_parser.eu.jpmorgan", "implemented": False},
    ("eu", "franklintempleton"): {"module": "etf_holdings_parser.eu.franklintempleton", "implemented": False},
    ("eu", "deka"): {"module": "etf_holdings_parser.eu.deka", "implemented": False},
    ("eu", "goldmansachs"): {"module": "etf_holdings_parser.eu.goldmansachs", "implemented": False},
    ("us", "ishares"): {"module": "etf_holdings_parser.us.ishares", "implemented": True},
    ("us", "spdr"): {"module": "etf_holdings_parser.us.spdr", "implemented": True},
    ("us", "vanguard"): {"module": "etf_holdings_parser.us.vanguard", "implemented": False},
    ("us", "invesco"): {"module": "etf_holdings_parser.us.invesco", "implemented": False},
    ("us", "schwab"): {"module": "etf_holdings_parser.us.schwab", "implemented": False},
    ("us", "jpmorgan"): {"module": "etf_holdings_parser.us.jpmorgan", "implemented": False},
    ("us", "fidelity"): {"module": "etf_holdings_parser.us.fidelity", "implemented": False},
    ("us", "dimensional"): {"module": "etf_holdings_parser.us.dimensional", "implemented": False},
    ("us", "firsttrust"): {"module": "etf_holdings_parser.us.firsttrust", "implemented": False},
    ("us", "wisdomtree"): {"module": "etf_holdings_parser.us.wisdomtree", "implemented": False},
}


def get_parser(region: str, issuer: str):
    """Return the `parse(raw: str) -> list[Holding]` function for (region, issuer).

    Raises KeyError if the (region, issuer) pair is unknown, or
    NotImplementedParser if it's registered but not yet ported.
    """
    entry = REGISTRY[(region, issuer)]
    if not entry["implemented"]:
        raise NotImplementedParser(f"{region}.{issuer} is registered but not yet implemented")
    module = importlib.import_module(str(entry["module"]))
    return module.parse


def list_parsers() -> list[tuple[str, str, bool]]:
    """All registered (region, issuer, implemented) tuples."""
    return [(region, issuer, bool(entry["implemented"])) for (region, issuer), entry in REGISTRY.items()]


def fee_drag(principal: float, annual_ter_pct: float, years: int, annual_growth_pct: float = 0.0) -> dict:
    """Cumulative cost of an ETF's TER on a given investment, in absolute
    currency terms — the number that actually matters for a "should I buy
    this ETF" decision, and that no provider hands you directly.

    Compares a portfolio compounding at `annual_growth_pct` with vs. without
    the TER drag, each year. With `annual_growth_pct=0` (the default), this
    is the TER's drag in isolation, undiluted by market growth — the
    conservative, comparison-friendly number ("what this ETF costs you no
    matter what the market does").

    Returns {"years": [...], "with_fee": [...], "without_fee": [...], "total_fee_drag": float}
    — one list entry per year so a screener can chart it, plus the final
    cumulative drag.
    """
    if principal < 0 or annual_ter_pct < 0 or years <= 0:
        raise ValueError("principal, annual_ter_pct must be >= 0 and years must be > 0")

    growth = 1 + annual_growth_pct / 100
    ter = annual_ter_pct / 100

    with_fee = principal
    without_fee = principal
    years_list, with_fee_list, without_fee_list = [], [], []
    for year in range(1, years + 1):
        without_fee *= growth
        with_fee *= growth * (1 - ter)
        years_list.append(year)
        with_fee_list.append(round(with_fee, 2))
        without_fee_list.append(round(without_fee, 2))

    return {
        "years": years_list,
        "with_fee": with_fee_list,
        "without_fee": without_fee_list,
        "total_fee_drag": round(without_fee_list[-1] - with_fee_list[-1], 2),
    }
