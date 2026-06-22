"""Parses iShares Europe/UCITS fund exports.

Verified 2026-06-23 against a live download of IGLN's (iShares Physical Gold
ETC) fund export, obtained via a headless browser (see
parser-worker/src/scrapers/eu_ishares.py — the real download link is behind
a cookie-consent banner and an investor-type/country gate, and isn't present
in the page's static HTML at all; it's added by client-side JS after both
are dismissed).

The real format is SpreadsheetML XML (Excel 2003 XML, despite a `.ajax?
fileType=xls` URL and `application/vnd.ms-excel` content-type — it is NOT a
binary .xls). For a single-asset ETC like IGLN there is no holdings list at
all (the fund holds physical gold bars, not securities) — the export has
"Overview"/"Historical"/"Performance" worksheets instead. `parse()` returns
one synthetic 100%-weighted holding describing the underlying asset in that
case, since EtfHoldingsProvider's contract expects *some* representation of
what the fund holds, and "100% Commodity" is the truthful answer.

Equity UCITS ranges (CSPX, IWDA, EIMI, etc.) have NOT been verified against a
real download — they may have a genuine "Holdings" worksheet instead. If you
capture one, add real per-row parsing for an "ss:Worksheet ss:Name=\"Holdings\""
section here rather than assuming this single-asset path applies.
"""

from __future__ import annotations

import re

from etf_holdings_parser.base import Holding, csv_rows, safe_float

_WORKSHEET_RE = re.compile(r'<ss:Worksheet ss:Name="([^"]*)">(.*?)</ss:Worksheet>', re.S)
_ROW_RE = re.compile(r"<ss:Row[^>]*>(.*?)</ss:Row>", re.S)
_CELL_RE = re.compile(r"<ss:Data[^>]*>(.*?)</ss:Data>", re.S)


def parse(raw: str) -> list[Holding]:
    if "ss:Workbook" in raw or raw.lstrip().startswith("<?xml"):
        return _parse_spreadsheetml(raw)
    return _parse_legacy_csv(raw)


def _parse_spreadsheetml(raw: str) -> list[Holding]:
    sheets = {name: body for name, body in _WORKSHEET_RE.findall(raw)}

    if "Holdings" in sheets:
        return _parse_holdings_sheet(sheets["Holdings"])

    if "Overview" in sheets:
        overview = _overview_key_values(sheets["Overview"])
        asset_class = overview.get("Asset Class", "")
        if asset_class:
            return [
                Holding(
                    name=f"{asset_class} (single-asset fund — see FundProfile, not a securities portfolio)",
                    asset_class=asset_class,
                    weight=100.0,
                )
            ]

    return []


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


def _parse_holdings_sheet(sheet_xml: str) -> list[Holding]:
    """Not yet verified against a real export — see module docstring. Best
    guess at the row shape based on iShares' US/legacy CSV column naming,
    kept here so a real sample can be slotted in without restructuring."""
    holdings: list[Holding] = []
    rows = []
    for row_xml in _ROW_RE.findall(sheet_xml):
        cells = [c.strip() for c in _CELL_RE.findall(row_xml)]
        if cells:
            rows.append(cells)
    if not rows:
        return holdings
    header = rows[0]
    for cells in rows[1:]:
        row = dict(zip(header, cells))
        name = row.get("Name", "").strip()
        if not name or name.startswith("-"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=row.get("Ticker", "").strip(),
                isin=row.get("ISIN", "").strip(),
                country=row.get("Location", row.get("Country", "")).strip(),
                sector=row.get("Sector", "").strip(),
                currency=row.get("Currency", "").strip(),
                asset_class=row.get("Asset Class", "").strip(),
                weight=safe_float(row.get("Weight (%)", "0")),
                shares=safe_float(row.get("Shares", "0")),
                market_value=safe_float(row.get("Market Value", "0")),
            )
        )
    return holdings


def _parse_legacy_csv(raw: str) -> list[Holding]:
    """Pre-2026-06-23 guessed format, kept only in case some fund's export
    really is a plain CSV — unverified, do not assume it's correct without a
    real sample."""
    holdings: list[Holding] = []
    for row in csv_rows(raw, skip_until_header_contains=("Name", "Weight")):
        name = row.get("Name", "").strip()
        if not name or name.startswith("-"):
            continue
        holdings.append(
            Holding(
                name=name,
                symbol=row.get("Ticker", "").strip(),
                isin=row.get("ISIN", "").strip(),
                country=row.get("Location", row.get("Country", "")).strip(),
                sector=row.get("Sector", "").strip(),
                currency=row.get("Currency", "").strip(),
                asset_class=row.get("Asset Class", "").strip(),
                weight=safe_float(row.get("Weight (%)", "0")),
                shares=safe_float(row.get("Shares", "0")),
                market_value=safe_float(row.get("Market Value", "0")),
            )
        )
    return holdings
