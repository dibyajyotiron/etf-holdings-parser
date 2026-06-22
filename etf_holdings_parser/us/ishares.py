"""Parses iShares US holdings CSV.

iShares' US site (blackrock.com) and Europe/UCITS site (ishares.com) publish
holdings through the same underlying BlackRock platform with an identical CSV
shape (metadata header block, then a row containing "Name"/"Weight"). Reuse
the EU module rather than duplicating the parsing logic — only the fetch URL
differs between the two domiciles, and fetching is the caller's job, not
this package's.
"""

from etf_holdings_parser.eu.ishares import parse

__all__ = ["parse"]
