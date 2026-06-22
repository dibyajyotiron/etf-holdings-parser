"""Stub: EU Lng holdings parser — not yet implemented.

TODO: capture a real sample export from Lng and port the actual
column mapping here, following the pattern in eu/vanguard.py or eu/ishares.py.
"""

from __future__ import annotations

from etf_holdings_parser.base import Holding, NotImplementedParser


def parse(raw: str) -> list[Holding]:
    raise NotImplementedParser("eu.lng parser not yet implemented")
