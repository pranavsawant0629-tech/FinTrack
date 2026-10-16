"""
Unit tests for the deterministic derivatives calculation tools.
Verifies option payoff formulas, breakevens, profit/loss bounds, futures P&L,
input validation, and option Greeks catalog.
"""

import pytest
from app.tools.derivatives.greeks import GREEKS_CATALOG, get_all_greeks, get_greek_info
from app.tools.derivatives.models import OptionPayoffResult, FuturesPayoffResult
from app.tools.derivatives.payoff import calculate_futures_pnl, calculate_option_payoff


class TestOptionPayoffCalculations:
    """Test mathematical accuracy of option payoff functions."""

    def test_long_call_payoff_exact_math(self):
        """Test Long Call: Strike=25000, Premium=150."""
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=25000.0,
            premium=150.0,
            spot_range=[24000.0, 25000.0, 25150.0, 25500.0],
        )
        assert isinstance(res, OptionPayoffResult)
        assert res.option_type == "call"
        assert res.position == "long"
        assert res.strike_price == 25000.0
        assert res.premium == 150.0
        assert res.breakeven_price == 25150.0
        assert res.max_profit == "Unlimited"
        assert res.max_loss == 150.0

        # Check spot outcomes
        points = {p.spot_price: p for p in res.payoff_table}
        # Below strike (OTM)
        assert points[24000.0].payoff == 0.0
        assert points[24000.0].pnl == -150.0
        # At strike (ATM)
        assert points[25000.0].payoff == 0.0
        assert points[25000.0].pnl == -150.0
        # At breakeven
        assert points[25150.0].payoff == 150.0
        assert points[25150.0].pnl == 0.0
        # In the money (ITM)
        assert points[25500.0].payoff == 500.0
        assert points[25500.0].pnl == 350.0

    def test_short_call_payoff_exact_math(self):
        """Test Short Call: Strike=25000, Premium=150."""
        res = calculate_option_payoff(
            option_type="call",
            position="short",
            strike_price=25000.0,
            premium=150.0,
            spot_range=[24500.0, 25000.0, 25150.0, 25500.0],
        )
        assert res.breakeven_price == 25150.0
        assert res.max_profit == 150.0
        assert res.max_loss == "Unlimited"

        points = {p.spot_price: p for p in res.payoff_table}
        # Below strike: seller retains full premium
        assert points[24500.0].pnl == 150.0
        # At breakeven: pnl is 0.0
        assert points[25150.0].pnl == 0.0
        # Above strike: seller incurs loss
        assert points[25500.0].pnl == -350.0

    def test_long_put_payoff_exact_math(self):
        """Test Long Put: Strike=25000, Premium=200."""
        res = calculate_option_payoff(
            option_type="put",
            position="long",
            strike_price=25000.0,
            premium=200.0,
            spot_range=[24000.0, 24800.0, 25000.0, 25500.0],
        )
        assert res.breakeven_price == 24800.0
        assert res.max_profit == 24800.0  # Strike - Premium
        assert res.max_loss == 200.0

        points = {p.spot_price: p for p in res.payoff_table}
        # Deep ITM
        assert points[24000.0].payoff == 1000.0
        assert points[24000.0].pnl == 800.0
        # Breakeven
        assert points[24800.0].payoff == 200.0
        assert points[24800.0].pnl == 0.0
        # ATM
        assert points[25000.0].payoff == 0.0
        assert points[25000.0].pnl == -200.0
        # OTM
        assert points[25500.0].payoff == 0.0
        assert points[25500.0].pnl == -200.0

    def test_short_put_payoff_exact_math(self):
        """Test Short Put: Strike=25000, Premium=200."""
        res = calculate_option_payoff(
            option_type="put",
            position="short",
            strike_price=25000.0,
            premium=200.0,
            spot_range=[24000.0, 24800.0, 25000.0, 26000.0],
        )
        assert res.breakeven_price == 24800.0
        assert res.max_profit == 200.0
        assert res.max_loss == 24800.0

        points = {p.spot_price: p for p in res.payoff_table}
        assert points[24000.0].pnl == -800.0
        assert points[24800.0].pnl == 0.0
        assert points[25000.0].pnl == 200.0
        assert points[26000.0].pnl == 200.0

    def test_default_spot_range_generation(self):
        """Test that omitting spot_range generates a valid discrete schedule around strike."""
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=1000.0,
            premium=50.0,
        )
        assert len(res.payoff_table) >= 9
        spot_prices = [p.spot_price for p in res.payoff_table]
        assert 1000.0 in spot_prices
        assert 1050.0 in spot_prices  # Breakeven included

    def test_invalid_parameters_raise_value_error(self):
        """Test input validation for invalid options arguments."""
        # Zero strike
        with pytest.raises(ValueError, match="Strike price must be strictly positive"):
            calculate_option_payoff("call", "long", 0.0, 50.0)

        # Negative strike
        with pytest.raises(ValueError, match="Strike price must be strictly positive"):
            calculate_option_payoff("call", "long", -100.0, 50.0)

        # Negative premium
        with pytest.raises(ValueError, match="Option premium cannot be negative"):
            calculate_option_payoff("call", "long", 1000.0, -10.0)

        # Invalid option type
        with pytest.raises(ValueError, match="Invalid option_type"):
            calculate_option_payoff("straddle", "long", 1000.0, 50.0)

        # Invalid position
        with pytest.raises(ValueError, match="Invalid position"):
            calculate_option_payoff("call", "neutral", 1000.0, 50.0)


class TestFuturesPayoffCalculations:
    """Test mathematical accuracy of futures P&L calculation."""

    def test_long_futures_pnl(self):
        """Test Long Futures: Entry=24000, Lot=25."""
        res = calculate_futures_pnl(
            position="long",
            entry_price=24000.0,
            lot_size=25,
            exit_prices=[23500.0, 24000.0, 24500.0],
        )
        assert isinstance(res, FuturesPayoffResult)
        assert res.position == "long"
        assert res.entry_price == 24000.0
        assert res.lot_size == 25
        assert res.breakeven_price == 24000.0

        points = {p.exit_price: p for p in res.payoff_table}
        assert points[23500.0].pnl_per_unit == -500.0
        assert points[23500.0].total_pnl == -12500.0

        assert points[24000.0].pnl_per_unit == 0.0
        assert points[24000.0].total_pnl == 0.0

        assert points[24500.0].pnl_per_unit == 500.0
        assert points[24500.0].total_pnl == 12500.0

    def test_short_futures_pnl(self):
        """Test Short Futures: Entry=24000, Lot=25."""
        res = calculate_futures_pnl(
            position="short",
            entry_price=24000.0,
            lot_size=25,
            exit_prices=[23500.0, 24000.0, 24500.0],
        )
        assert res.position == "short"
        points = {p.exit_price: p for p in res.payoff_table}
        # Falling price profits short position
        assert points[23500.0].total_pnl == 12500.0
        assert points[24000.0].total_pnl == 0.0
        assert points[24500.0].total_pnl == -12500.0

    def test_futures_validation(self):
        """Test input validation for futures calculations."""
        with pytest.raises(ValueError, match="Entry price must be strictly positive"):
            calculate_futures_pnl("long", 0.0, 25)

        with pytest.raises(ValueError, match="Lot size must be strictly positive"):
            calculate_futures_pnl("long", 24000.0, 0)

        with pytest.raises(ValueError, match="Invalid position"):
            calculate_futures_pnl("hedge", 24000.0, 25)


class TestGreeksCatalog:
    """Test Greeks educational definitions."""

    def test_all_standard_greeks_present(self):
        greeks = get_all_greeks()
        for expected in ["delta", "gamma", "theta", "vega", "rho"]:
            assert expected in greeks
            info = greeks[expected]
            assert info.name.lower() == expected
            assert len(info.symbol) > 0
            assert len(info.definition) > 0
            assert len(info.range_or_bound) > 0
            assert len(info.pedagogical_example) > 0

    def test_get_greek_info(self):
        delta = get_greek_info("Delta")
        assert delta is not None
        assert delta.name == "Delta"
        assert "0.0 to +1.0" in delta.range_or_bound

        unknown = get_greek_info("nonexistent_greek")
        assert unknown is None

    def test_zero_premium_boundary_case(self):
        """Test option payoff calculation when premium is exactly 0."""
        res = calculate_option_payoff("call", "long", 100.0, 0.0, spot_range=[90.0, 100.0, 110.0])
        assert res.breakeven_price == 100.0
        assert res.max_loss == 0.0
        points = {p.spot_price: p for p in res.payoff_table}
        assert points[90.0].pnl == 0.0
        assert points[110.0].pnl == 10.0

    def test_fractional_strike_and_premium(self):
        """Test handling of fractional strikes and premiums."""
        res = calculate_option_payoff("put", "long", 24050.50, 12.75, spot_range=[24000.0])
        assert res.breakeven_price == 24037.75
        points = {p.spot_price: p for p in res.payoff_table}
        assert points[24000.0].payoff == 50.50
        assert points[24000.0].pnl == 37.75

    def test_case_insensitivity(self):
        """Test that arguments are case-insensitive."""
        res = calculate_option_payoff("CALL", "LONG", 1000.0, 50.0)
        assert res.option_type == "call"
        assert res.position == "long"

        res_put = calculate_option_payoff("pUt", "sHoRt", 1000.0, 50.0)
        assert res_put.option_type == "put"
        assert res_put.position == "short"

    def test_specific_greeks_definitions(self):
        """Test specific values for Theta and Vega."""
        theta = get_greek_info("theta")
        assert theta is not None
        assert "Time Decay" in theta.definition or "Time to expiration" in theta.primary_driver

        vega = get_greek_info("vega")
        assert vega is not None
        assert "Volatility" in vega.primary_driver
