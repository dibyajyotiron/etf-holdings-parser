import pytest

from etf_holdings_parser import fee_drag


def test_zero_growth_isolates_fee_cost():
    result = fee_drag(principal=10000, annual_ter_pct=0.20, years=10)
    assert result["years"] == list(range(1, 11))
    assert result["without_fee"][-1] == 10000.0  # no growth, no fee -> unchanged
    # 0.2% annual drag compounded over 10 years on $10k
    assert result["with_fee"][-1] < 10000.0
    assert result["total_fee_drag"] > 0


def test_total_fee_drag_matches_last_year_difference():
    result = fee_drag(principal=10000, annual_ter_pct=0.5, years=5, annual_growth_pct=7.0)
    assert result["total_fee_drag"] == round(result["without_fee"][-1] - result["with_fee"][-1], 2)


def test_higher_ter_costs_more():
    cheap = fee_drag(principal=10000, annual_ter_pct=0.07, years=20, annual_growth_pct=7.0)
    expensive = fee_drag(principal=10000, annual_ter_pct=0.75, years=20, annual_growth_pct=7.0)
    assert expensive["total_fee_drag"] > cheap["total_fee_drag"]


def test_rejects_invalid_input():
    with pytest.raises(ValueError):
        fee_drag(principal=-1, annual_ter_pct=0.2, years=10)
    with pytest.raises(ValueError):
        fee_drag(principal=10000, annual_ter_pct=0.2, years=0)
