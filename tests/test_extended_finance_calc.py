"""
Unit tests for extended deterministic financial calculation engine.
Covers:
- Compound Annual Growth Rate (CAGR)
- Real Inflation-Adjusted Return (Fisher Equation)
- Rule of 72 Doubling Tenure vs Exact Logarithmic Compounding
- Sharpe and Sortino Ratios (calculate_risk_adjusted_metrics)
- Boundary, zero-variance, and zero-downside handling
"""

import math
import pytest
from app.tools.calc.extended import (
    calculate_cagr,
    calculate_real_return,
    calculate_rule_of_72,
)
from app.tools.portfolio.metrics import (
    FREQUENCY_MULTIPLIERS,
    calculate_risk_adjusted_metrics,
)


class TestCAGRCalculation:
    """Tests for Compound Annual Growth Rate (CAGR)."""

    def test_cagr_standard_positive(self):
        """100,000 to 200,000 over 5 years is approx 14.87%."""
        res = calculate_cagr(initial_value=100000.0, final_value=200000.0, tenure_years=5.0)
        assert res["cagr_decimal"] == pytest.approx(0.148698, rel=1e-4)
        assert res["cagr_percent"] == 14.87
        assert res["initial_value"] == 100000.0
        assert res["final_value"] == 200000.0
        assert res["tenure_years"] == 5.0
        assert res["absolute_gain"] == 100000.0
        assert res["total_growth_percent"] == 100.0

    def test_cagr_fractional_years(self):
        """CAGR with fractional year period (2.5 years)."""
        res = calculate_cagr(initial_value=50000.0, final_value=65000.0, tenure_years=2.5)
        # (65000/50000)^(1/2.5) - 1 = 1.3^0.4 - 1 = 0.11065... -> 11.07%
        assert res["cagr_percent"] == 11.07

    def test_cagr_sub_day_tenure(self):
        """Tenure shorter than one day (e.g. 0.5/365 years) is mathematically valid and accepted."""
        sub_day_tenure = 0.5 / 365.0
        res = calculate_cagr(initial_value=100000.0, final_value=100100.0, tenure_years=sub_day_tenure)
        assert res["cagr_percent"] > 0
        assert res["tenure_years"] == round(sub_day_tenure, 4)

    def test_cagr_negative_growth_loss(self):
        """CAGR over an investment loss."""
        res = calculate_cagr(initial_value=100000.0, final_value=50000.0, tenure_years=3.0)
        # (0.5)^(1/3) - 1 approx -0.2063
        assert res["cagr_percent"] == -20.63
        assert res["absolute_gain"] == -50000.0
        assert res["total_growth_percent"] == -50.0

    def test_cagr_zero_ending_value(self):
        """Total loss ending in zero value yields -100% CAGR."""
        res = calculate_cagr(initial_value=10000.0, final_value=0.0, tenure_years=2.0)
        assert res["cagr_percent"] == -100.0
        assert res["cagr_decimal"] == -1.0

    def test_cagr_invalid_inputs(self):
        """Validation checks for invalid CAGR parameters."""
        with pytest.raises(ValueError, match="Initial investment value must be strictly positive"):
            calculate_cagr(0.0, 1000.0, 3.0)

        with pytest.raises(ValueError, match="Initial investment value must be strictly positive"):
            calculate_cagr(-500.0, 1000.0, 3.0)

        with pytest.raises(ValueError, match="Final investment value cannot be negative"):
            calculate_cagr(1000.0, -100.0, 3.0)

        with pytest.raises(ValueError, match="Tenure in years must be strictly positive"):
            calculate_cagr(1000.0, 2000.0, 0.0)

        with pytest.raises(ValueError, match="Tenure in years must be strictly positive"):
            calculate_cagr(1000.0, 2000.0, -2.0)


class TestRealReturnCalculation:
    """Tests for Inflation-Adjusted Return via the exact Fisher equation."""

    def test_real_return_exact_fisher(self):
        """12% nominal return with 6% inflation."""
        # Fisher equation: (1 + 0.12) / (1 + 0.06) - 1 = 1.12 / 1.06 - 1 approx 0.0566038 -> 5.66%
        res = calculate_real_return(nominal_return_pct=12.0, inflation_rate_pct=6.0)
        assert res["real_return_percent"] == 5.66
        assert res["real_return_decimal"] == pytest.approx(0.056604, rel=1e-4)
        assert res["nominal_return_percent"] == 12.0
        assert res["inflation_rate_percent"] == 6.0
        # Simple subtraction would give 6.0%, verify exact Fisher is different
        assert res["real_return_percent"] != 6.0

    def test_real_return_zero_inflation(self):
        """Zero inflation means real return equals nominal return."""
        res = calculate_real_return(nominal_return_pct=8.5, inflation_rate_pct=0.0)
        assert res["real_return_percent"] == 8.5
        assert res["real_return_decimal"] == 0.085

    def test_real_return_negative_inflation_deflation(self):
        """Deflation (-2% inflation) increases real purchasing power."""
        res = calculate_real_return(nominal_return_pct=5.0, inflation_rate_pct=-2.0)
        # (1 + 0.05) / (1 - 0.02) - 1 = 1.05 / 0.98 - 1 approx 7.14%
        assert res["real_return_percent"] == 7.14

    def test_real_return_negative_real_rate(self):
        """Nominal return lower than inflation yields negative real return."""
        res = calculate_real_return(nominal_return_pct=4.0, inflation_rate_pct=7.0)
        # 1.04 / 1.07 - 1 approx -0.028037 -> -2.80%
        assert res["real_return_percent"] == -2.80

    def test_real_return_invalid_inputs(self):
        """Inflation of -100% or worse destroys division."""
        with pytest.raises(ValueError, match="Inflation rate cannot be -100% or lower"):
            calculate_real_return(nominal_return_pct=10.0, inflation_rate_pct=-100.0)

        with pytest.raises(ValueError, match="Inflation rate cannot be -100% or lower"):
            calculate_real_return(nominal_return_pct=10.0, inflation_rate_pct=-110.0)


class TestRuleOf72Calculation:
    """Tests for Rule of 72 doubling tenure estimation vs exact logarithmic compounding."""

    def test_rule_of_72_standard_8_pct(self):
        """8% annual return: Rule of 72 gives 9.0 years; exact is ln(2)/ln(1.08) = 9.01 years."""
        res = calculate_rule_of_72(annual_rate_pct=8.0)
        assert res["approximate_doubling_years"] == 9.0
        assert res["exact_doubling_years"] == 9.01
        assert res["estimation_discrepancy_years"] == 0.01

    def test_rule_of_72_high_return_divergence(self):
        """24% annual return: Rule of 72 gives 3.0 years; exact is ln(2)/ln(1.24) = 3.22 years."""
        res = calculate_rule_of_72(annual_rate_pct=24.0)
        assert res["approximate_doubling_years"] == 3.0
        assert res["exact_doubling_years"] == 3.22
        assert res["estimation_discrepancy_years"] == 0.22

    def test_rule_of_72_very_high_annual_rate(self):
        """Rates above 1000% (e.g. 1500%) are accepted without arbitrary caps."""
        res = calculate_rule_of_72(annual_rate_pct=1500.0)
        assert res["approximate_doubling_years"] == round(72.0 / 1500.0, 2)
        assert res["exact_doubling_years"] > 0

    def test_rule_of_72_invalid_inputs(self):
        """Annual rate <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="Annual rate must be strictly positive"):
            calculate_rule_of_72(0.0)

        with pytest.raises(ValueError, match="Annual rate must be strictly positive"):
            calculate_rule_of_72(-5.0)


class TestSharpeAndSortinoMetrics:
    """Tests for deterministic Sharpe and Sortino ratio evaluation."""

    def test_sharpe_and_sortino_daily_frequency(self):
        """Test daily returns with explicit daily Rf and daily MAR."""
        daily_returns = [0.005, -0.002, 0.008, 0.001, -0.004, 0.007, 0.003, -0.001, 0.006, 0.002]
        # Periodic risk-free: 6% annualized / 252
        daily_rf = 0.06 / 252
        daily_mar = 0.0

        res = calculate_risk_adjusted_metrics(
            returns=daily_returns,
            risk_free_rate=daily_rf,
            mar=daily_mar,
            frequency="daily",
        )

        assert res.frequency == "daily"
        assert res.frequency_multiplier == 252
        assert res.observation_count == 10
        assert res.sharpe_status == "ok"
        assert res.sortino_status == "ok"

        # Check annualization math:
        # Annualized return = periodic_mean * 252
        assert res.annualized_mean_return == pytest.approx(res.periodic_mean_return * 252, rel=1e-3)
        # Annualized std dev = periodic_std * sqrt(252)
        assert res.annualized_std_dev == pytest.approx(res.periodic_std_dev * math.sqrt(252), rel=1e-3)
        # Annualized Sharpe = periodic_sharpe * sqrt(252)
        assert res.annualized_sharpe_ratio == pytest.approx(res.periodic_sharpe_ratio * math.sqrt(252), rel=1e-3)
        # Annualized Sortino = periodic_sortino * sqrt(252)
        assert res.annualized_sortino_ratio == pytest.approx(res.periodic_sortino_ratio * math.sqrt(252), rel=1e-3)

    def test_sharpe_and_sortino_monthly_frequency(self):
        """Test monthly returns with explicit monthly Rf and MAR."""
        monthly_returns = [0.02, 0.03, -0.01, 0.015, -0.005, 0.04, 0.01, 0.025, -0.02, 0.03]
        monthly_rf = 0.06 / 12  # 0.005
        monthly_mar = 0.005

        res = calculate_risk_adjusted_metrics(
            returns=monthly_returns,
            risk_free_rate=monthly_rf,
            mar=monthly_mar,
            frequency="monthly",
        )

        assert res.frequency == "monthly"
        assert res.frequency_multiplier == 12
        assert res.observation_count == 10
        assert res.annualized_mean_return == pytest.approx(res.periodic_mean_return * 12, rel=1e-5)
        assert res.annualized_std_dev == pytest.approx(res.periodic_std_dev * math.sqrt(12), rel=1e-5)

    def test_degrees_of_freedom_boundary_condition(self):
        """Fewer than 3 observations must raise ValueError with clear algorithmic explanation."""
        with pytest.raises(ValueError, match="Minimum 3 periodic return observations required"):
            calculate_risk_adjusted_metrics(returns=[0.01, 0.02], risk_free_rate=0.001)

        with pytest.raises(ValueError, match="Minimum 3 periodic return observations required"):
            calculate_risk_adjusted_metrics(returns=[0.05], risk_free_rate=0.001)

        with pytest.raises(ValueError, match="Minimum 3 periodic return observations required"):
            calculate_risk_adjusted_metrics(returns=[], risk_free_rate=0.001)

    def test_zero_variance_constant_returns(self):
        """Identical returns produce zero standard deviation -> Sharpe ratio undefined."""
        constant_returns = [0.02, 0.02, 0.02, 0.02]
        res = calculate_risk_adjusted_metrics(
            returns=constant_returns,
            risk_free_rate=0.01,
            mar=0.01,
            frequency="annual",
        )
        assert res.periodic_std_dev == 0.0
        assert res.periodic_sharpe_ratio is None
        assert res.annualized_sharpe_ratio is None
        assert res.sharpe_status == "undefined_zero_variance"

    def test_zero_downside_deviation_all_above_mar(self):
        """All returns exceed MAR -> downside deviation is 0.0 -> Sortino ratio undefined."""
        stellar_returns = [0.05, 0.08, 0.06, 0.07]
        mar = 0.02  # All returns are strictly greater than MAR
        res = calculate_risk_adjusted_metrics(
            returns=stellar_returns,
            risk_free_rate=0.01,
            mar=mar,
            frequency="annual",
        )
        assert res.periodic_downside_dev == 0.0
        assert res.periodic_sortino_ratio is None
        assert res.annualized_sortino_ratio is None
        assert res.sortino_status == "undefined_zero_downside"
        # Sharpe should still be valid because variance is non-zero
        assert res.periodic_sharpe_ratio is not None
        assert res.sharpe_status == "ok"

    def test_annual_frequency_multiplier_one(self):
        """Annual frequency has k=1, so annualized equals periodic."""
        annual_returns = [0.12, -0.05, 0.18, 0.08, 0.15]
        res = calculate_risk_adjusted_metrics(
            returns=annual_returns,
            risk_free_rate=0.06,
            mar=0.06,
            frequency="annual",
        )
        assert res.frequency_multiplier == 1
        assert res.periodic_mean_return == res.annualized_mean_return
        assert res.periodic_std_dev == res.annualized_std_dev
        assert res.periodic_sharpe_ratio == res.annualized_sharpe_ratio
        assert res.periodic_sortino_ratio == res.annualized_sortino_ratio
