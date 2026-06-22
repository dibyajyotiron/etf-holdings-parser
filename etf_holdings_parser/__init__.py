"""etf_holdings_parser: pure parsers for ETF issuer holdings exports.

No network code lives here — see README.md. Callers fetch raw text and call
the matching `<region>.<issuer>.parse(raw)` function directly, or use
`get_parser(region, issuer)` to look one up dynamically.
"""

from etf_holdings_parser.base import (
    Holding,
    NotImplementedParser,
    get_parser,
    list_parsers,
)

__all__ = ["Holding", "NotImplementedParser", "get_parser", "list_parsers"]
__version__ = "0.1.0"
