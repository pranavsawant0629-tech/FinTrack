"""Stage 7D: Deterministic Tool Boundary and Correctness Tests.

Validates:
1. Correct Long Put Breakeven formula (Strike - Premium) and feasible breakeven flag.
2. Derivatives payoff strategies (Call, Put, Long, Short).
3. Extreme value rejection in derivatives calculator (> 1e12).
4. Financial math calculators (Compounding, SIP, 50/30/20, Emergency Fund).
5. Market data validator boundary conditions (NaN, Inf, negative prices, inverted high/low).
"""

from __future__ import annotations

import math
import pytest

from app.tools.calc.budget import calculate_50_30_20
from app.tools.calc.compounding import calculate_compound_interest, calculate_sip
from app.tools.calc.emergency_fund import calculate_emergency_fund
from app.tools.derivatives.payoff import calculate_option_payoff
from app.tools.market.interfaces import DataValidationError
from app.tools.market.models import (
    CompanyOverview,
    HistoricalPrices,
    MarketQuote,
)
from app.tools.market.validator import MarketDataValidator


# ==============================================================================
# 1. Derivatives Payoff & Correct Long Put Breakeven Tests
# ==============================================================================

class TestDerivativesBoundaryCorrectness:
    """Tests for options payoff strategies and boundary rules."""

    def test_long_put_breakeven_standard(self):
        """Standard Long Put: Strike = 100, Premium = 20 -> Breakeven = 80.0."""
        res = calculate_option_payoff(
            option_type="put",
            position="long",
            strike_price=100.0,
            premium=20.0,
            spot_range=[60.0, 80.0, 100.0, 120.0],
        )
        assert res.breakeven_price == 80.0
        assert res.has_feasible_breakeven is True
        assert res.max_loss == 20.0
        assert res.max_profit == 80.0  # Strike - Premium at spot=0

    def test_long_put_breakeven_negative_unclamped(self):
        """Critical Rule: When Premium > Strike, breakeven = Strike - Premium < 0.
        Must NOT clamp to zero, and has_feasible_breakeven must be False.
        """
        res = calculate_option_payoff(
            option_type="put",
            position="long",
            strike_price=100.0,
            premium=150.0,
            spot_range=[0.0, 50.0, 100.0],
        )
        assert res.breakeven_price == -50.0
        assert res.has_feasible_breakeven is False
        assert res.max_loss == 150.0

    def test_long_call_breakeven(self):
        """Standard Long Call: Strike = 100, Premium = 15 -> Breakeven = 115.0."""
        res = calculate_option_payoff(
            option_type="call",
            position="long",
            strike_price=100.0,
            premium=15.0,
            spot_range=[80.0, 100.0, 115.0, 130.0],
        )
        assert res.breakeven_price == 115.0
        assert res.has_feasible_breakeven is True
        assert res.max_loss == 15.0
        assert res.max_profit == "Unlimited"

    def test_short_call_payoff(self):
        """Short Call: Strike = 100, Premium = 10 -> Breakeven = 110.0, Max profit = 10.0."""
        res = calculate_option_payoff(
            option_type="call",
            position="short",
            strike_price=100.0,
            premium=10.0,
            spot_range=[90.0, 100.0, 110.0, 120.0],
        )
        assert res.breakeven_price == 110.0
        assert res.max_profit == 10.0
        assert res.max_loss == "Unlimited"

    def test_short_put_payoff(self):
        """Short Put: Strike = 100, Premium = 15 -> Breakeven = 85.0, Max profit = 15.0."""
        res = calculate_option_payoff(
            option_type="put",
            position="short",
            strike_price=100.0,
            premium=15.0,
            spot_range=[70.0, 85.0, 100.0],
        )
        assert res.breakeven_price == 85.0
        assert res.has_feasible_breakeven is True
        assert res.max_profit == 15.0
        assert res.max_loss == 85.0

    def test_extreme_values_rejected(self):
        """Values > 1e12 or negative must raise ValueError."""
        with pytest.raises(ValueError, match="exceeds maximum allowable bound"):
            calculate_option_payoff(
                option_type="call",
                position="long",
                strike_price=2e12,
                premium=10.0,
            )

        with pytest.raises(ValueError, match="exceeds maximum allowable bound"):
            calculate_option_payoff(
                option_type="put",
                position="long",
                strike_price=100.0,
                premium=2e12,
            )

        with pytest.raises(ValueError, match="must be strictly positive"):
            calculate_option_payoff(
                option_type="call",
                position="long",
                strike_price=-100.0,
                premium=10.0,
            )


# ==============================================================================
# 2. Financial Math Calculator Boundary Tests
# ==============================================================================

class TestFinancialMathBoundaryCorrectness:
    """Tests for compounding, SIP, budget, and emergency fund calculators."""

    def test_compounding_standard(self):
        """Compound interest: 100000 @ 10% for 5 years compounded annually."""
        res = calculate_compound_interest(
            principal=100000,
            annual_rate_pct=10.0,
            tenure_years=5,
            compounding_frequency=1,
        )
        expected = round(100000 * (1.10 ** 5), 2)
        assert res["maturity_amount"] == expected
        assert res["interest_earned"] == round(expected - 100000, 2)

    def test_compounding_negative_values_raise(self):
        """Negative principal, rate, or years must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_compound_interest(principal=-1000, annual_rate_pct=5.0, tenure_years=2)

        with pytest.raises(ValueError):
            calculate_compound_interest(principal=1000, annual_rate_pct=-5.0, tenure_years=2)

        with pytest.raises(ValueError):
            calculate_compound_interest(principal=1000, annual_rate_pct=5.0, tenure_years=-2)

    def test_sip_calculator_standard(self):
        """SIP: 5000/month @ 12% for 10 years."""
        res = calculate_sip(
            monthly_investment=5000,
            annual_return_pct=12.0,
            tenure_years=10,
        )
        assert res["total_invested"] == 600000.0
        assert res["future_value"] > res["total_invested"]
        assert res["wealth_gain"] == round(res["future_value"] - res["total_invested"], 2)

    def test_sip_negative_values_raise(self):
        """Negative monthly investment or years must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_sip(monthly_investment=-5000, annual_return_pct=10.0, tenure_years=5)

        with pytest.raises(ValueError):
            calculate_sip(monthly_investment=5000, annual_return_pct=10.0, tenure_years=0)

    def test_budget_50_30_20(self):
        """50/30/20 rule: 100,000 monthly income."""
        res = calculate_50_30_20(income=100000.0)
        assert res["needs"] == 50000.0
        assert res["wants"] == 30000.0
        assert res["savings"] == 20000.0

    def test_budget_negative_income_raises(self):
        """Negative or zero monthly income must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_50_30_20(income=-5000.0)

        with pytest.raises(ValueError):
            calculate_50_30_20(income=0.0)

    def test_emergency_fund(self):
        """Emergency fund: 40000/month for 6 months."""
        res = calculate_emergency_fund(monthly_expenses=40000.0, target_months=6.0)
        assert res["target_fund"] == 240000.0
        assert res["target_months"] == 6.0

    def test_emergency_fund_negative_raises(self):
        """Negative expenses or months must raise ValueError."""
        with pytest.raises(ValueError):
            calculate_emergency_fund(monthly_expenses=-1000.0, target_months=6.0)

        with pytest.raises(ValueError):
            calculate_emergency_fund(monthly_expenses=1000.0, target_months=0.0)


# ==============================================================================
# 3. Market Data Validator Boundary Tests
# ==============================================================================

class TestMarketDataValidatorBoundaries:
    """Tests for NaN, Inf, and sanity validations in market data."""

    @pytest.fixture
    def validator(self) -> MarketDataValidator:
        return MarketDataValidator()

    @pytest.fixture
    def valid_quote(self) -> MarketQuote:
        return MarketQuote(
            symbol="RELIANCE",
            company_name="Reliance Industries Ltd.",
            exchange="NSE",
            currency="INR",
            price=2900.0,
            change=25.0,
            change_percent=0.87,
            previous_close=2875.0,
            open=2880.0,
            high=2920.0,
            low=2870.0,
            volume=5000000,
            market_status="closed",
            market_timestamp="2026-03-30T15:30:00+05:30",
            retrieved_at="2026-03-30T15:35:00+05:30",
            provider="mock_nse",
        )

    def test_valid_quote_passes(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """Normal valid quote must pass validation."""
        normalized = validator.validate_quote(valid_quote)
        assert normalized.symbol == "RELIANCE"
        assert normalized.price == 2900.0

    def test_nan_price_rejected(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """NaN price must raise DataValidationError."""
        valid_quote.price = float("nan")
        with pytest.raises(DataValidationError, match="Invalid non-positive quote price"):
            validator.validate_quote(valid_quote)

    def test_inf_price_rejected(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """Inf price must raise DataValidationError."""
        valid_quote.price = float("inf")
        with pytest.raises(DataValidationError, match="Invalid non-positive quote price"):
            validator.validate_quote(valid_quote)

    def test_negative_price_rejected(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """Negative price must raise DataValidationError."""
        valid_quote.price = -100.0
        with pytest.raises(DataValidationError, match="Invalid non-positive quote price"):
            validator.validate_quote(valid_quote)

    def test_inverted_high_low_rejected(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """High < Low must raise DataValidationError."""
        valid_quote.high = 2800.0
        valid_quote.low = 2900.0
        with pytest.raises(DataValidationError, match="cannot be lower than day low"):
            validator.validate_quote(valid_quote)

    def test_price_exceeds_high_rejected(self, validator: MarketDataValidator, valid_quote: MarketQuote):
        """Price > High must raise DataValidationError."""
        valid_quote.price = 3000.0
        valid_quote.high = 2950.0
        with pytest.raises(DataValidationError, match="cannot exceed day high"):
            validator.validate_quote(valid_quote)

    def test_historical_nan_rejected(self, validator: MarketDataValidator):
        """NaN in historical data must raise DataValidationError."""
        hist = HistoricalPrices(
            symbol="TCS",
            start_date="2026-02-01",
            end_date="2026-03-01",
            start_price=float("nan"),
            end_price=4000.0,
            period_change=100.0,
            period_change_percent=2.5,
            period_high=4100.0,
            period_low=3900.0,
            provider="mock",
            retrieved_at="2026-03-01T00:00:00Z",
        )
        with pytest.raises(DataValidationError, match="non-finite historical"):
            validator.validate_historical(hist)

    def test_overview_nan_rejected(self, validator: MarketDataValidator):
        """NaN in overview metrics must raise DataValidationError."""
        overview = CompanyOverview(
            symbol="INFY",
            company_name="Infosys Ltd",
            provider="mock",
            retrieved_at="2026-03-01T00:00:00Z",
            market_cap=float("nan"),
        )
        with pytest.raises(DataValidationError, match="non-finite overview"):
            validator.validate_overview(overview)
