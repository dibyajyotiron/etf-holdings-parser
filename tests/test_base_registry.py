import pytest

from etf_holdings_parser.base import NotImplementedParser, get_parser, list_parsers


def test_implemented_parser_resolves():
    parse = get_parser("eu", "vanguard")
    assert callable(parse)


def test_unimplemented_parser_raises():
    with pytest.raises(NotImplementedParser):
        get_parser("eu", "xtrackers")


def test_list_parsers_reports_implementation_status():
    parsers = list_parsers()
    assert ("eu", "vanguard", True) in parsers
    assert ("eu", "xtrackers", False) in parsers
