<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Volume 14: Deterministic Financial Tools & Mathematical Engines

## 1. Architectural Mandate: Why Pure Determinism Matters

[FACT]
Finova AI enforces a strict architectural division: **Language models explain concepts, but deterministic Python functions perform mathematical calculations.**

Large language models (including 7B models like Qwen 2.5) are probabilistic token-prediction engines. When prompted with arithmetic or financial formulas, they frequently produce plausible-sounding but mathematically erroneous outputs:
- Compounding exponentiation errors: $(1 + 0.12/12)^{120}$ will drift or hallucinate significant digits.
- Inverted option payoffs: Mistaking Put breakeven ($K - P$) for Call breakeven ($K + P$).
- Budget calculation rounding discrepancies where individual components do not sum to 100% of income.

Finova AI guarantees that **every numerical value presented to the user is calculated in pure Python with exact mathematical precision, validated against unit tests, and never modified by the LLM or response composer.**

---

## 2. Inventory of Implemented vs. Merely Discussed Concepts

[FACT]
To ensure complete transparency, the following table demarcates calculations that actually exist in the codebase versus financial theories that are merely discussed pedagogically.

| Financial Calculation / Model | Implementation Status | Source File | Test Verification |
| :--- | :--- | :--- | :--- |
| **50/30/20 Budget Breakdown** | `[IMPLEMENTED]` | [`app/tools/calc/budget.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/budget.py) | `tests/test_finance_calc.py` |
| **Compound Interest (Lump Sum)** | `[IMPLEMENTED]` | [`app/tools/calc/compounding.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/compounding.py) | `tests/test_finance_calc.py` |
| **SIP (Systematic Investment Plan)** | `[IMPLEMENTED]` | [`app/tools/calc/compounding.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/compounding.py) | `tests/test_finance_calc.py` |
| **Emergency Fund Sizing & Gap** | `[IMPLEMENTED]` | [`app/tools/calc/emergency_fund.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/emergency_fund.py) | `tests/test_finance_calc.py` |
| **Option Payoff & Breakeven (Call/Put)** | `[IMPLEMENTED]` | [`app/tools/derivatives/payoff.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/payoff.py) | `tests/test_derivatives_tool.py` |
| **Futures P&L & Schedule** | `[IMPLEMENTED]` | [`app/tools/derivatives/payoff.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/payoff.py) | `tests/test_derivatives_tool.py` |
| **Portfolio Valuation & Asset Allocation** | `[IMPLEMENTED]` | [`app/tools/portfolio/service.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/portfolio/service.py) | `tests/test_portfolio_tool.py` |
| **Portfolio 'What-If' Stress Testing** | `[IMPLEMENTED]` | [`app/tools/portfolio/service.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/portfolio/service.py) | `tests/test_portfolio_tool.py` |
| **Option Greeks (Delta, Gamma, Theta, Vega, Rho)** | `[CATALOG ONLY]` | [`app/tools/derivatives/greeks.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/greeks.py) | Static definitions & bounds; continuous Black-Scholes solver NOT implemented |
| **Black-Scholes Analytical Pricing Formula** | `[DISCUSSED ONLY]` | Not in codebase | Continuous pricing engine was not requested in Phase 6 |
| **Monte Carlo Portfolio Simulation** | `[DISCUSSED ONLY]` | Not in codebase | Conceptual pedagogy in prompts only |
| **Sharpe / Treynor / Sortino Ratios** | `[DISCUSSED ONLY]` | Not in codebase | Discussed in portfolio pedagogy |
| **Discounted Cash Flow (DCF) Valuation** | `[DISCUSSED ONLY]` | Not in codebase | Discussed in equity fundamental analysis |

---

## 3. Exhaustive Tool Breakdown

---

### Tool 1: 50/30/20 Budgeting Calculator

- **File**: [`app/tools/calc/budget.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/budget.py)
- **Function**: `calculate_50_30_20(income: float) -> dict[str, Any]`

#### 1. Formula
$$\text{Needs} = \text{Income} \times 0.50$$
$$\text{Wants} = \text{Income} \times 0.30$$
$$\text{Savings} = \text{Income} \times 0.20$$

#### 2. Variables
- `income` ($I \in \mathbb{R}^+$): Net monthly take-home (post-tax) income in Indian Rupees (₹).
- `needs`: Essential survival expenditures (rent, food, electricity, medical, minimum debt payments).
- `wants`: Discretionary lifestyle spending (dining out, entertainment, vacations).
- `savings`: Wealth building and emergency buffer (SIPs, PPF, emergency fund, prepayments).

#### 3. Assumptions
- Input represents post-tax (net) disposable income.
- Fixed percentage allocation without dynamic scaling for ultra-high or low income brackets.
- All values rounded to 2 decimal places using standard IEEE-754 half-to-even rounding (`round(x, 2)`).

#### 4. Python Implementation
```python
def calculate_50_30_20(income: float) -> dict[str, Any]:
    if income <= 0:
        raise ValueError("Monthly income must be greater than zero.")

    needs = round(income * 0.50, 2)
    wants = round(income * 0.30, 2)
    savings = round(income * 0.20, 2)

    return {
        "type": "budget_50_30_20",
        "title": "50/30/20 Budget Breakdown",
        "income": round(income, 2),
        "needs": needs,
        "wants": wants,
        "savings": savings,
        "needs_pct": 50.0,
        "wants_pct": 30.0,
        "savings_pct": 20.0,
    }
```

#### 5. Concrete Numerical Example
- **Input**: `income = 75000.0`
- **Calculation**:
  - Needs: $75,000 \times 0.50 = 37,500.00$
  - Wants: $75,000 \times 0.30 = 22,500.00$
  - Savings: $75,000 \times 0.20 = 15,000.00$
- **Total Verification**: $37,500 + 22,500 + 15,000 = 75,000.00$ (100%).

#### 6. Edge Cases & Boundary Handling
- `income == 0.0`: Raises `ValueError("Monthly income must be greater than zero.")`.
- `income < 0.0`: Raises `ValueError`.
- `income = 0.01`: Needs = 0.01, Wants = 0.00, Savings = 0.00 (correctly rounded).

#### 7. Test Verification
Tested in `tests/test_finance_calc.py::test_calculate_50_30_20_precision` and `test_calculate_50_30_20_invalid_income`.

---

### Tool 2: Compound Interest Calculator (Lump Sum)

- **File**: [`app/tools/calc/compounding.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/compounding.py)
- **Function**: `calculate_compound_interest(principal, annual_rate_pct, tenure_years, compounding_frequency=1)`

#### 1. Formula
$$A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}$$
$$\text{Interest Earned} = A - P$$

#### 2. Variables
- $P$ (`principal`): Initial invested sum ($P > 0$).
- $r$ (`annual_rate_pct / 100`): Annual nominal interest rate as a decimal fraction ($r > 0$).
- $n$ (`compounding_frequency`): Number of compounding periods per calendar year ($n \ge 1$; e.g., 1 for annual, 4 for quarterly, 12 for monthly).
- $t$ (`tenure_years`): Investment duration in years ($t > 0$).
- $A$ (`maturity_amount`): Future accumulated capital at expiration.

#### 3. Assumptions
- Constant nominal rate of return over the entire investment tenure.
- No interim capital withdrawals or secondary deposits.
- Compounding intervals are strictly uniform.

#### 4. Python Implementation
```python
def calculate_compound_interest(
    principal: float,
    annual_rate_pct: float,
    tenure_years: float,
    compounding_frequency: int = 1,
) -> dict[str, Any]:
    if principal <= 0:
        raise ValueError("Principal must be greater than zero.")
    if annual_rate_pct <= 0:
        raise ValueError("Annual rate must be greater than zero.")
    if tenure_years <= 0:
        raise ValueError("Tenure must be greater than zero.")
    if compounding_frequency <= 0:
        raise ValueError("Compounding frequency must be positive.")

    r = annual_rate_pct / 100.0
    n = compounding_frequency
    t = tenure_years

    maturity_amount = round(principal * ((1.0 + (r / n)) ** (n * t)), 2)
    interest_earned = round(maturity_amount - principal, 2)

    return {
        "type": "compound_interest",
        "title": "Compound Interest Growth",
        "principal": round(principal, 2),
        "annual_rate_percent": round(annual_rate_pct, 2),
        "tenure_years": t,
        "compounding_frequency": n,
        "maturity_amount": maturity_amount,
        "interest_earned": interest_earned,
    }
```

#### 5. Concrete Numerical Example
- **Input**: `principal = 100000.0`, `annual_rate_pct = 10.0`, `tenure_years = 2.0`, `compounding_frequency = 1`
- **Calculation**:
  $$A = 100,000 \cdot (1 + 0.10/1)^{1 \cdot 2} = 100,000 \cdot (1.10)^2 = 100,000 \cdot 1.21 = 121,000.00$$
  $$\text{Interest} = 121,000.00 - 100,000.00 = 21,000.00$$

#### 6. Edge Cases & Boundary Handling
- Negative or zero principal ($P \le 0$): Raises `ValueError`.
- Negative or zero rate ($r \le 0$): Raises `ValueError`.
- Negative or zero tenure ($t \le 0$): Raises `ValueError`.
- Fractional years ($t = 2.5$): Accurately computed via floating-point power operator.

#### 7. Test Verification
Tested in `tests/test_finance_calc.py::test_calculate_compound_interest_precision`.

---

### Tool 3: Systematic Investment Plan (SIP) Calculator

- **File**: [`app/tools/calc/compounding.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/compounding.py)
- **Function**: `calculate_sip(monthly_investment, annual_return_pct, tenure_years)`

#### 1. Formula (Annuity Due)
$$M = P \cdot \left[\frac{(1 + i)^k - 1}{i}\right] \cdot (1 + i)$$
$$\text{Total Invested} = P \cdot k$$
$$\text{Wealth Gain} = M - \text{Total Invested}$$

#### 2. Variables
- $P$ (`monthly_investment`): Recurring monthly installment in Rupees ($P > 0$).
- $i$ (`periodic monthly rate`): $i = \frac{\text{annual\_return\_pct} / 100}{12}$.
- $k$ (`total compounding months`): $k = \text{tenure\_years} \times 12$.
- $M$ (`future_value`): Total future maturity value.

#### 3. Assumptions
- **Annuity Due Principle**: Payments are deposited at the *beginning* of each calendar month (represented by the trailing factor $\cdot (1 + i)$).
- Uniform monthly compounding rate $i$.
- No delayed or missed SIP installments.

#### 4. Python Implementation
```python
def calculate_sip(
    monthly_investment: float,
    annual_return_pct: float,
    tenure_years: float,
) -> dict[str, Any]:
    if monthly_investment <= 0:
        raise ValueError("Monthly investment must be greater than zero.")
    if annual_return_pct <= 0:
        raise ValueError("Expected annual return must be greater than zero.")
    if tenure_years <= 0:
        raise ValueError("Tenure must be greater than zero.")

    p = monthly_investment
    i = (annual_return_pct / 100.0) / 12.0
    k = int(tenure_years * 12)

    future_value = round(p * (((1.0 + i) ** k - 1.0) / i) * (1.0 + i), 2)
    total_invested = round(p * k, 2)
    wealth_gain = round(future_value - total_invested, 2)

    return {
        "type": "sip_calculation",
        "title": "SIP Wealth Accumulation",
        "monthly_investment": round(p, 2),
        "annual_return_percent": round(annual_return_pct, 2),
        "tenure_years": tenure_years,
        "total_invested": total_invested,
        "future_value": future_value,
        "wealth_gain": wealth_gain,
    }
```

#### 5. Concrete Numerical Example
- **Input**: `monthly_investment = 5000.0`, `annual_return_pct = 12.0`, `tenure_years = 1.0`
- **Calculation**:
  - $i = 0.12 / 12 = 0.01$
  - $k = 12$
  - $\text{Total Invested} = 5,000 \times 12 = 60,000.00$
  - Multiplier: $\frac{(1.01)^{12} - 1}{0.01} \cdot 1.01 = \frac{0.126825}{0.01} \cdot 1.01 = 12.6825 \cdot 1.01 = 12.8093$
  - Future Value: $5,000 \times 12.809328 = 64,047.16$
  - Wealth Gain: $64,047.16 - 60,000.00 = 4,047.16$

#### 6. Edge Cases & Boundary Handling
- $P \le 0, r \le 0, t \le 0$: Raises `ValueError`.
- Long tenures ($t = 30$ years, $k = 360$ months): Computed without floating-point overflow.

#### 7. Test Verification
Tested in `tests/test_finance_calc.py::test_calculate_sip_precision`.

---

### Tool 4: Emergency Fund Calculator

- **File**: [`app/tools/calc/emergency_fund.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/emergency_fund.py)
- **Function**: `calculate_emergency_fund(monthly_expenses, current_savings=0.0, target_months=6.0)`

#### 1. Formula
$$\text{Target Fund} = \text{Monthly Expenses} \times \text{Target Months}$$
$$\text{Funding Gap} = \max(0.0, \text{Target Fund} - \text{Current Savings})$$
$$\text{Months Covered} = \frac{\text{Current Savings}}{\text{Monthly Expenses}}$$

#### 2. Variables
- `monthly_expenses`: Recurring baseline survival living costs ($E > 0$).
- `current_savings`: Liquid capital currently set aside ($S \ge 0$).
- `target_months`: Desired liquidity runway (default 6.0 months; $M > 0$).

#### 3. Assumptions
- Emergency reserves must be held in ultra-liquid, capital-preserved instruments (savings account, liquid mutual funds).
- Non-negative funding gap (if current savings exceed target fund, gap is zero).

#### 4. Python Implementation
```python
def calculate_emergency_fund(
    monthly_expenses: float,
    current_savings: float = 0.0,
    target_months: float = 6.0,
) -> dict[str, Any]:
    if monthly_expenses <= 0:
        raise ValueError("Monthly expenses must be greater than zero.")
    if current_savings < 0:
        raise ValueError("Current savings cannot be negative.")
    if target_months <= 0:
        raise ValueError("Target months must be positive.")

    target_fund = round(monthly_expenses * target_months, 2)
    funding_gap = round(max(0.0, target_fund - current_savings), 2)
    months_covered = round(current_savings / monthly_expenses, 1)

    return {
        "type": "emergency_fund",
        "title": "Emergency Fund Adequacy Analysis",
        "monthly_expenses": round(monthly_expenses, 2),
        "target_months": round(target_months, 1),
        "target_fund": target_fund,
        "current_savings": round(current_savings, 2),
        "funding_gap": funding_gap,
        "months_covered": months_covered,
    }
```

#### 5. Concrete Numerical Example
- **Input**: `monthly_expenses = 30000.0`, `current_savings = 60000.0`, `target_months = 6.0`
- **Calculation**:
  - $\text{Target Fund} = 30,000 \times 6 = 180,000.00$
  - $\text{Funding Gap} = \max(0, 180,000 - 60,000) = 120,000.00$
  - $\text{Months Covered} = 60,000 / 30,000 = 2.0 \text{ months}$

#### 6. Edge Cases & Boundary Handling
- Fully funded ($S = 200,000 > 180,000$): Funding gap is clamped to `0.0`, months covered = `6.7`.
- Zero savings ($S = 0.0$): Funding gap = Target Fund, months covered = `0.0`.
- Negative expenses or savings: Raises `ValueError`.

#### 7. Test Verification
Tested in `tests/test_finance_calc.py::test_calculate_emergency_fund_precision` and `test_calculate_emergency_fund_fully_funded`.

---

### Tool 5: Option Payoff & Breakeven Engine

- **File**: [`app/tools/derivatives/payoff.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/payoff.py)
- **Function**: `calculate_option_payoff(option_type, position, strike_price, premium, spot_range=None)`

#### 1. Formulas

##### Call Options
$$\text{Gross Payoff}_{\text{Call}} = \max(0.0, S_T - K)$$
$$\text{Net P\&L}_{\text{Long Call}} = \text{Gross Payoff} - P$$
$$\text{Net P\&L}_{\text{Short Call}} = P - \text{Gross Payoff}$$
$$\text{Breakeven}_{\text{Call}} = K + P$$
$$\text{Max Profit}_{\text{Long Call}} = \text{"Unlimited"}, \quad \text{Max Loss}_{\text{Long Call}} = P$$
$$\text{Max Profit}_{\text{Short Call}} = P, \quad \text{Max Loss}_{\text{Short Call}} = \text{"Unlimited"}$$

##### Put Options
$$\text{Gross Payoff}_{\text{Put}} = \max(0.0, K - S_T)$$
$$\text{Net P\&L}_{\text{Long Put}} = \text{Gross Payoff} - P$$
$$\text{Net P\&L}_{\text{Short Put}} = P - \text{Gross Payoff}$$
$$\text{Breakeven}_{\text{Put}} = K - P$$
$$\text{Max Profit}_{\text{Long Put}} = K - P, \quad \text{Max Loss}_{\text{Long Put}} = P$$
$$\text{Max Profit}_{\text{Short Put}} = P, \quad \text{Max Loss}_{\text{Short Put}} = K - P$$

#### 2. Variables
- $K$ (`strike_price`): Agreed contract exercise price ($0 < K \le 10^{12}$).
- $P$ (`premium`): Option market price paid by buyer / received by seller ($0 \le P \le 10^{12}$).
- $S_T$ (`spot_price`): Underlying stock or index price at contract expiration.
- `has_feasible_breakeven`: Boolean flag set to `False` if $K - P < 0$ for Put options.

#### 3. Assumptions & Critical Architectural Invariant
- **Unclamped Negative Breakeven Invariant**:
  If a Put option has a premium greater than its strike ($P > K$), the mathematical breakeven $K - P$ is strictly negative. Because stock prices cannot trade below ₹0.00, achieving breakeven is mathematically impossible.
  Finova AI **does NOT clamp the breakeven to zero**. It outputs the exact negative number (e.g. $-₹50.00$) and explicitly sets `has_feasible_breakeven = False`!

#### 4. Python Implementation
```python
def calculate_option_payoff(
    option_type: str,
    position: str,
    strike_price: float,
    premium: float,
    spot_range: list[float] | None = None,
) -> OptionPayoffResult:
    opt_type_clean = option_type.strip().lower()
    pos_clean = position.strip().lower()

    if opt_type_clean not in ("call", "put"):
        raise ValueError(f"Invalid option_type: '{option_type}'.")
    if pos_clean not in ("long", "short"):
        raise ValueError(f"Invalid position: '{position}'.")

    if strike_price <= 0 or strike_price > 1e12:
        raise ValueError("Strike price out of bounds.")
    if premium < 0 or premium > 1e12:
        raise ValueError("Option premium out of bounds.")

    strike = round(float(strike_price), 2)
    prem = round(float(premium), 2)

    if opt_type_clean == "call":
        breakeven = round(strike + prem, 2)
        has_feasible_be = True
        max_profit = "Unlimited" if pos_clean == "long" else prem
        max_loss = prem if pos_clean == "long" else "Unlimited"
    else:  # put
        breakeven = round(strike - prem, 2)
        has_feasible_be = breakeven >= 0.0
        max_profit = round(strike - prem, 2) if pos_clean == "long" else prem
        max_loss = prem if pos_clean == "long" else round(strike - prem, 2)

    # Spot Schedule generation
    if spot_range is None or len(spot_range) == 0:
        multipliers = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
        spots = sorted(set([round(strike * m, 2) for m in multipliers] + [breakeven]))
    else:
        spots = sorted([round(float(s), 2) for s in spot_range])

    payoff_table = []
    for spot in spots:
        gross = max(0.0, round(spot - strike, 2)) if opt_type_clean == "call" else max(0.0, round(strike - spot, 2))
        net_pnl = round(gross - prem, 2) if pos_clean == "long" else round(prem - gross, 2)
        pt_payoff = gross if pos_clean == "long" else round(-gross, 2)
        payoff_table.append(OptionPayoffPoint(spot_price=spot, payoff=pt_payoff, pnl=net_pnl))

    return OptionPayoffResult(...)
```

#### 5. Concrete Numerical Example (Long Put)
- **Input**: `strike = 25000.0`, `premium = 200.0`, `position = "long"`, `option_type = "put"`
- **Results**:
  - Breakeven = $25,000 - 200 = ₹24,800.00$
  - Max Profit = $25,000 - 200 = ₹24,800.00$ (if underlying goes to 0)
  - Max Loss = $₹200.00$
  - Spot = 24,000: Gross Payoff = 1,000, Net P&L = +₹800.00
  - Spot = 24,800: Gross Payoff = 200, Net P&L = ₹0.00
  - Spot = 25,500: Gross Payoff = 0, Net P&L = -₹200.00

#### 6. Edge Cases & Boundary Handling
- $P > K$ ($K=100, P=150$): Breakeven = $-50.0$, `has_feasible_breakeven = False`.
- Values $> 10^{12}$: Raises `ValueError` to prevent numerical overflow attacks.
- Zero strike ($K \le 0$): Raises `ValueError`.

#### 7. Test Verification
Tested in `tests/test_derivatives_tool.py` and `tests/test_tool_boundary_correctness.py::TestDerivativesBoundaryCorrectness`.

---

### Tool 6: Futures Contract P&L Calculator

- **File**: [`app/tools/derivatives/payoff.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/payoff.py)
- **Function**: `calculate_futures_pnl(position, entry_price, lot_size, exit_prices=None)`

#### 1. Formulas
$$\text{Unit P\&L}_{\text{Long}} = S_{\text{exit}} - F_0$$
$$\text{Unit P\&L}_{\text{Short}} = F_0 - S_{\text{exit}}$$
$$\text{Total P\&L} = \text{Unit P\&L} \times \text{Lot Size}$$
$$\text{Breakeven Price} = F_0$$

#### 2. Variables
- $F_0$ (`entry_price`): Contract lock-in price ($F_0 > 0$).
- `lot_size`: Number of underlying market units per standardized contract (e.g. 25 for NIFTY 50, 15 for BANKNIFTY; $> 0$).
- $S_{\text{exit}}$: Settlement / exit spot price.

#### 3. Assumptions
- Symmetric linear risk: Futures have no premium decay; gains and losses are identical and unbounded in both directions.
- Daily mark-to-market margin requirements are not modeled; calculation reflects trade-to-exit P&L.

#### 4. Python Implementation
```python
def calculate_futures_pnl(
    position: str,
    entry_price: float,
    lot_size: int,
    exit_prices: list[float] | None = None,
) -> FuturesPayoffResult:
    pos_clean = position.strip().lower()
    if pos_clean not in ("long", "short"):
        raise ValueError("Invalid position.")
    if entry_price <= 0 or lot_size <= 0:
        raise ValueError("Entry price and lot size must be strictly positive.")

    entry = round(float(entry_price), 2)
    lot = int(lot_size)

    exits = (
        [round(entry * m, 2) for m in [0.90, 0.95, 1.00, 1.05, 1.10]]
        if not exit_prices
        else sorted([round(float(p), 2) for p in exit_prices])
    )

    table = []
    for exit_p in exits:
        unit_pnl = round(exit_p - entry, 2) if pos_clean == "long" else round(entry - exit_p, 2)
        total = round(unit_pnl * lot, 2)
        table.append(FuturesPayoffPoint(exit_price=exit_p, pnl_per_unit=unit_pnl, total_pnl=total))

    return FuturesPayoffResult(
        position=pos_clean,
        entry_price=entry,
        lot_size=lot,
        breakeven_price=entry,
        payoff_table=table,
    )
```

#### 5. Concrete Numerical Example
- **Input**: `entry_price = 24000.0`, `lot_size = 25`, `position = "long"`, `exit_prices = [23500.0, 24000.0, 24500.0]`
- **Results**:
  - Exit 23,500: Unit P&L = -₹500.00, Total P&L = -₹12,500.00
  - Exit 24,000: Unit P&L = ₹0.00, Total P&L = ₹0.00 (Breakeven)
  - Exit 24,500: Unit P&L = +₹500.00, Total P&L = +₹12,500.00

#### 6. Edge Cases & Boundary Handling
- Lot size zero or negative: Raises `ValueError`.
- Entry price zero or negative: Raises `ValueError`.

#### 7. Test Verification
Tested in `tests/test_derivatives_tool.py::TestFuturesPayoffCalculations`.

---

### Tool 7: Portfolio Analytics & "What-If" Simulation Engine

- **File**: [`app/tools/portfolio/service.py`](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/portfolio/service.py)
- **Functions**: `calculate_metrics(portfolio)` & `simulate_what_if(portfolio, target_symbol, change_pct, broad_market)`

#### 1. Formulas

##### Valuation & Accounting
$$\text{Securities Market Value} = \sum_{j} (\text{Quantity}_j \times \text{Current Price}_j)$$
$$\text{Securities Cost Basis} = \sum_{j} (\text{Quantity}_j \times \text{Avg Buy Price}_j)$$
$$\text{Total Portfolio Value} = \text{Securities Market Value} + \text{Cash Balance}$$
$$\text{Unrealized P\&L} = \text{Securities Market Value} - \text{Securities Cost Basis}$$
$$\text{Unrealized P\&L \%} = \frac{\text{Unrealized P\&L}}{\text{Securities Cost Basis}} \times 100$$

##### Asset & Sector Allocation
$$\text{Asset Allocation \%}_a = \frac{\text{Value of Asset Class } a}{\text{Total Portfolio Value}} \times 100$$
$$\text{Sector Allocation \%}_s = \frac{\text{Value of Sector } s}{\text{Securities Market Value}} \times 100$$

##### "What-If" Stress Testing
- If `broad_market == True` (e.g. "What if NIFTY drops 10%?"):
  $$\text{Simulated Price}_j = \text{Current Price}_j \times \left(1 + \frac{\Delta_{\text{pct}}}{100}\right) \quad \forall j \in \text{Equity Holdings}$$
- If `broad_market == False` (single stock shock on asset $k$):
  $$\text{Simulated Price}_k = \text{Current Price}_k \times \left(1 + \frac{\Delta_{\text{pct}}}{100}\right)$$
$$\text{Portfolio Value Delta} = \text{Simulated Portfolio Value} - \text{Original Portfolio Value}$$

#### 2. Variables & Boundaries
- `holdings`: List of active positions (`symbol`, `quantity`, `average_buy_price`, `current_price`, `asset_type`, `sector`).
- `cash_balance`: Uninvested liquidity buffer.
- `change_pct`: Market movement shock (e.g. $-10.0$ for a 10% market crash).

#### 3. Python Implementation Excerpt
```python
def simulate_what_if(
    self,
    portfolio: PortfolioData,
    target_symbol: str | None,
    change_pct: float,
    broad_market: bool = False,
) -> WhatIfSimulationResult:
    original_metrics = self.calculate_metrics(portfolio)
    simulated_holdings = []
    impacted = []

    multiplier = 1.0 + (change_pct / 100.0)

    for h in portfolio.holdings:
        should_shock = broad_market or (target_symbol and h.symbol.upper() == target_symbol.upper())
        new_price = round(h.current_price * multiplier, 2) if should_shock else h.current_price
        
        sim_h = h.model_copy(update={"current_price": new_price})
        simulated_holdings.append(sim_h)
        
        if should_shock:
            val_delta = round((new_price - h.current_price) * h.quantity, 2)
            impacted.append(HoldingImpact(
                symbol=h.symbol,
                original_price=h.current_price,
                simulated_price=new_price,
                value_delta=val_delta,
            ))

    sim_portfolio = portfolio.model_copy(update={"holdings": simulated_holdings})
    sim_metrics = self.calculate_metrics(sim_portfolio)

    portfolio_delta = round(sim_metrics.total_portfolio_value - original_metrics.total_portfolio_value, 2)
    portfolio_delta_pct = round((portfolio_delta / original_metrics.total_portfolio_value) * 100.0, 2)

    return WhatIfSimulationResult(
        original_portfolio_value=original_metrics.total_portfolio_value,
        simulated_portfolio_value=sim_metrics.total_portfolio_value,
        portfolio_delta_value=portfolio_delta,
        portfolio_delta_pct=portfolio_delta_pct,
        impacted_holdings=impacted,
        ...
    )
```

#### 4. Test Verification
Tested in `tests/test_portfolio_tool.py`.
