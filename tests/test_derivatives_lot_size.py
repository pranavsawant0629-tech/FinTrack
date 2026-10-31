"""
Unit tests verifying lot size parameterization for derivatives calculation tools.
Tests contract multipliers (1, 15, 25, 50, 75), total contract P&L/payoff,
total premiums, and strict input validation.
"""

import pytest
from app.tools.derivatives.payoff import calculate_option_payoff


class TestOptionLotSizeParameterization:
    """Tests option payoff with parameterized lot sizes."""

    @pytest.mark.parametrize("lot_size", [1, 15, 25, 50, 75, 100])
    def test_long_call_total_contract_math(self, lot_size: int):
        """Verify contract totals scale exactly by lot_size."""
        strike = 24000.0
        premium = 120.0
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=strike,
            premium=premium,
            spot_range=[23500.0, 24000.0, 24120.0, 24500.0],
            lot_size=lot_size,
        )

        assert res.lot_size == lot_size
        assert res.premium == 120.0
        assert res.total_premium == round(120.0 * lot_size, 2)
        assert res.max_profit == "Unlimited"
        assert res.total_max_profit == "Unlimited"
        assert res.max_loss == 120.0
        assert res.total_max_loss == round(120.0 * lot_size, 2)

        # Check discrete spot points
        points = {p.spot_price: p for p in res.payoff_table}
        for spot, pt in points.items():
            assert pt.total_payoff == round(pt.payoff * lot_size, 2)
            assert pt.total_pnl == round(pt.pnl * lot_size, 2)

        # Deep OTM: spot 23500
        assert points[23500.0].payoff == 0.0
        assert points[23500.0].total_payoff == 0.0
        assert points[23500.0].pnl == -120.0
        assert points[23500.0].total_pnl == round(-120.0 * lot_size, 2)

        # Breakeven: spot 24120
        assert points[24120.0].pnl == 0.0
        assert points[24120.0].total_pnl == 0.0

        # ITM: spot 24500 (gross payoff 500, net pnl 380)
        assert points[24500.0].payoff == 500.0
        assert points[24500.0].total_payoff == round(500.0 * lot_size, 2)
        assert points[24500.0].pnl == 380.0
        assert points[24500.0].total_pnl == round(380.0 * lot_size, 2)

    @pytest.mark.parametrize("lot_size", [1, 25, 50])
    def test_short_put_total_contract_math(self, lot_size: int):
        """Verify short put total max profit and loss scaling."""
        strike = 25000.0
        premium = 200.0
        res = calculate_option_payoff(
            option_type="put",
            position="short",
            strike_price=strike,
            premium=premium,
            spot_range=[24000.0, 24800.0, 25000.0, 25500.0],
            lot_size=lot_size,
        )

        assert res.lot_size == lot_size
        assert res.total_premium == round(200.0 * lot_size, 2)
        assert res.max_profit == 200.0
        assert res.total_max_profit == round(200.0 * lot_size, 2)
        assert res.max_loss == 24800.0
        assert res.total_max_loss == round(24800.0 * lot_size, 2)

        points = {p.spot_price: p for p in res.payoff_table}
        for spot, pt in points.items():
            assert pt.total_payoff == round(pt.payoff * lot_size, 2)
            assert pt.total_pnl == round(pt.pnl * lot_size, 2)

    def test_default_lot_size_is_one(self):
        """Omitting lot_size defaults to 1."""
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=1000.0,
            premium=50.0,
        )
        assert res.lot_size == 1
        assert res.total_premium == 50.0
        assert res.total_max_loss == 50.0

    def test_large_lot_size_accepted(self):
        """Very large positive integer lot sizes (e.g. 5,000,000) must be accepted without arbitrary caps."""
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=100.0,
            premium=5.0,
            lot_size=5000000,
        )
        assert res.lot_size == 5000000
        assert res.total_premium == 25000000.0
        assert res.total_max_loss == 25000000.0

    def test_invalid_lot_size_raises_value_error(self):
        """Lot size must be a strictly positive integer; rejects zero, negative, boolean, and float."""
        with pytest.raises(ValueError, match="Lot size must be a strictly positive integer"):
            calculate_option_payoff("call", "long", 1000.0, 50.0, lot_size=0)

        with pytest.raises(ValueError, match="Lot size must be a strictly positive integer"):
            calculate_option_payoff("call", "long", 1000.0, 50.0, lot_size=-25)

        with pytest.raises(ValueError, match="Lot size must be a strictly positive integer"):
            calculate_option_payoff("call", "long", 1000.0, 50.0, lot_size=True)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="Lot size must be a strictly positive integer"):
            calculate_option_payoff("call", "long", 1000.0, 50.0, lot_size=25.5)  # type: ignore[arg-type]

