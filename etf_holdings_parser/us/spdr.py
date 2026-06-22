"""Parses SPDR/State Street US holdings export (ssga.com daily holdings file).

Verified 2026-06-22 against a live download of SPY's holdings xlsx (the
caller converts xlsx -> CSV before handing it to `parse`; see
parser-worker/src/scrapers/us_spdr.py for the metadata-preamble handling
that conversion needs). Real columns observed for SPY: Name, Ticker,
Identifier, SEDOL, Weight, Sector, Shares Held, Local Currency — no Country,
Asset Class, or Market Value column on this fund's export (left unset below;
other SPDR funds may include them, hence the fallback column names).

"Identifier" is the security's CUSIP for US holdings, not an ISIN — do not
treat it as one. Only a column literally named "ISIN" (present on some
international SPDR funds) is used for the `isin` field.
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, csv_rows, safe_float


def parse(raw: str) -> list[Holding]:
    holdings: list[Holding] = []
    for row in csv_rows(raw):
        name = (row.get("Name") or row.get("Security Name") or "").strip()
        if not name or name.lower().startswith("total"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=(row.get("Ticker") or "").strip(),
                isin=(row.get("ISIN") or "").strip(),
                country=(row.get("Country") or "").strip(),
                sector=(row.get("Sector") or row.get("GICS Sector") or "").strip(),
                currency=(row.get("Local Currency") or row.get("Currency") or "").strip(),
                asset_class=(row.get("Asset Class") or "").strip(),
                weight=safe_float(row.get("Weight") or row.get("Weight (%)") or "0"),
                shares=safe_float(row.get("Shares Held") or row.get("Shares") or "0"),
                market_value=safe_float(row.get("Market Value") or "0"),
            )
        )
    return holdings
