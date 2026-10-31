"""
Simulated portfolio calculation tools and provider interfaces.
"""

from app.tools.portfolio.interfaces import BasePortfolioProvider
from app.tools.portfolio.metrics import (
    FREQUENCY_MULTIPLIERS,
    FrequencyType,
    RiskAdjustedMetricsResult,
    calculate_risk_adjusted_metrics,
)
from app.tools.portfolio.models import (
    AssetType,
    Holding,
    PortfolioData,
    PortfolioMetrics,
    WhatIfHoldingImpact,
    WhatIfSimulationResult,
)
from app.tools.portfolio.providers import MockPortfolioProvider, create_demo_portfolio
from app.tools.portfolio.service import PortfolioService, portfolio_service

__all__ = [
    "AssetType",
    "Holding",
    "PortfolioData",
    "PortfolioMetrics",
    "WhatIfHoldingImpact",
    "WhatIfSimulationResult",
    "BasePortfolioProvider",
    "MockPortfolioProvider",
    "create_demo_portfolio",
    "PortfolioService",
    "portfolio_service",
    "calculate_risk_adjusted_metrics",
    "RiskAdjustedMetricsResult",
    "FrequencyType",
    "FREQUENCY_MULTIPLIERS",
]
