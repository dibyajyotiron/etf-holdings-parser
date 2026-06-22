# etf-holdings-parser

Pure parsing logic for ETF issuer holdings exports (CSV/XML), normalized to one
common record shape. This package does **no network I/O** — callers (e.g. a
scraper that knows each issuer's URL pattern) fetch the raw text and pass it
in; modules here only parse.

## Normalized holding shape

```python
{
    "name": str,
    "symbol": str,
    "isin": str,
    "country": str,
    "sector": str,
    "currency": str,
    "asset_class": str,
    "weight": float,        # percent, 0-100
    "shares": float,
    "market_value": float,
}
```

## Layout

- `etf_holdings_parser/base.py` — shared types, CSV helpers, the registry of implemented parsers
- `etf_holdings_parser/us/*.py` — one module per US issuer
- `etf_holdings_parser/eu/*.py` — one module per EU-domiciled issuer (Ireland, Luxembourg, Germany, France, ...)
- `etf_holdings_parser/sec_nport.py` — parses an edgartools N-PORT holdings object

Each module exposes `parse(raw: str) -> list[dict]`.

## Status

Implemented: `eu.vanguard`, `eu.ishares`, `us.ishares`, `us.spdr`, `sec_nport`.
All other modules listed in `base.IMPLEMENTED`/`base.PLANNED` are stubs that raise
`NotImplementedError` until their real CSV/XML format is captured and ported —
see each module's docstring for the TODO.
