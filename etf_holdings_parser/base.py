"""Shared types and helpers for issuer holdings parsers."""

from __future__ import annotations

import csv
import importlib
import io
from typing import TypedDict


class Holding(TypedDict, total=False):
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


class NotImplementedParser(NotImplementedError):
    """Raised by a stub module whose real CSV/XML format hasn't been ported yet."""


def safe_float(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
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
    ("eu", "amundi"): {"module": "etf_holdings_parser.eu.amundi", "implemented": False},
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
