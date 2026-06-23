"""Parses iShares Europe/UCITS fund exports.

Two genuinely different real formats, both verified 2026-06-23 via a headless
browser (parser-worker/src/scrapers/eu_ishares.py — both download links are
behind a cookie-consent banner and an investor-type/country gate that aren't
in the page's static HTML at all; added by client-side JS after both are
cleared):

1. **Equity UCITS with real constituents** (CSPX verified: 511 real holdings).
   The "...&fileType=csv&fileName={TICKER}_holdings&dataType=fund" link is a
   plain CSV (NOT XML, despite some other iShares links on the same page
   being SpreadsheetML XML) with one metadata preamble line ("Fund Holdings
   as of,...") then a real header row. Columns: Ticker, Name, Sector, Asset
   Class, Market Value, Weight (%), Notional Value, Shares, Price, Location,
   Exchange, Market Currency. No ISIN column. A fund page can have several
   `.ajax` links (e.g. CSPX has a "_holdings" CSV, a "_collateralSnapshot"
   CSV for securities-lending collateral, and a "_fund" xlsx overview) — the
   fetcher must pick the one whose fileName contains "_holdings", not just
   the first `.ajax` link found.

2. **Single-asset ETC, no constituents** (IGLN verified: physical gold ETC).
   The "...&fileType=xls&fileName={TICKER}_fund&dataType=fund" link IS
   SpreadsheetML XML (Excel 2003 XML, despite the `.ajax?fileType=xls` URL
   and `application/vnd.ms-excel` content-type) with Overview/Historical/
   Performance worksheets and no holdings list at all — there's nothing to
   hold a list of, the fund just holds physical gold bars. `parse()` returns
   one synthetic 100%-weighted holding describing the asset in that case.
"""

from __future__ import annotations

import re

from etf_holdings_parser.base import Holding, csv_rows, safe_float

_WORKSHEET_RE = re.compile(r'<ss:Worksheet ss:Name="([^"]*)">(.*?)</ss:Worksheet>', re.S)
_ROW_RE = re.compile(r"<ss:Row[^>]*>(.*?)</ss:Row>", re.S)
_CELL_RE = re.compile(r"<ss:Data[^>]*>(.*?)</ss:Data>", re.S)


def parse(raw: str) -> list[Holding]:
    if "ss:Workbook" in raw or raw.lstrip().startswith("<?xml"):
        return _parse_single_asset_overview(raw)
    return _parse_holdings_csv(raw)


def _parse_holdings_csv(raw: str) -> list[Holding]:
    """Verified real format — see module docstring point 1 (CSPX)."""
    holdings: list[Holding] = []
    for row in csv_rows(raw, skip_until_header_contains=("Name", "Weight")):
        name = (row.get("Name") or "").strip()
        if not name or name.startswith("-"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=(row.get("Ticker") or "").strip(),
                isin="",  # not present in this export
                country=(row.get("Location") or "").strip(),
                sector=(row.get("Sector") or "").strip(),
                currency=(row.get("Market Currency") or "").strip(),
                asset_class=(row.get("Asset Class") or "").strip(),
                weight=safe_float(row.get("Weight (%)") or "0"),
                shares=safe_float(row.get("Shares") or "0"),
                market_value=safe_float(row.get("Market Value") or "0"),
            )
        )
    return holdings


def _parse_single_asset_overview(raw: str) -> list[Holding]:
    """Verified real format — see module docstring point 2 (IGLN)."""
    sheets = {name: body for name, body in _WORKSHEET_RE.findall(raw)}
    if "Overview" not in sheets:
        return []
    overview = _overview_key_values(sheets["Overview"])
    asset_class = overview.get("Asset Class", "")
    if not asset_class:
        return []
    return [
        Holding(
            name=f"{asset_class} (single-asset fund — see FundProfile, not a securities portfolio)",
            asset_class=asset_class,
            weight=100.0,
        )
    ]


def _overview_key_values(sheet_xml: str) -> dict[str, str]:
    """The Overview sheet is a title row, a disclaimer paragraph, then
    Label/Value pairs — not a table with a header row, so we read it as
    key-value rows rather than via csv_rows."""
    values: dict[str, str] = {}
    for row_xml in _ROW_RE.findall(sheet_xml):
        cells = [c.strip() for c in _CELL_RE.findall(row_xml)]
        if len(cells) == 2:
            values[cells[0]] = cells[1]
    return values
