"""
Utility helper functions for the German Real Estate Investment Analysis System.

Contains financial calculations, formatting functions, and common utilities.
"""

import numpy as np
import numpy_financial as npf
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import locale


def format_currency(value: float, currency: str = "EUR") -> str:
    """
    Format a number as German currency.

    Args:
        value: The numeric value to format
        currency: Currency code (default EUR)

    Returns:
        Formatted currency string (e.g., "123.456,78 €")
    """
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
    except locale.Error:
        pass

    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:,.2f} Mio. €".replace(",", "X").replace(".", ",").replace("X", ".")
    elif abs(value) >= 1_000:
        return f"{value:,.0f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a number as percentage (German format).

    Args:
        value: The numeric value (0.05 = 5%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    pct_value = value * 100
    return f"{pct_value:,.{decimals}f}%".replace(".", ",")


def format_number(value: float, decimals: int = 0) -> str:
    """Format number with German thousand separator."""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calculate_annuity(
    principal: float,
    annual_rate: float,
    years: int,
    payments_per_year: int = 12
) -> float:
    """
    Calculate the periodic payment (annuity) for a loan.

    Uses the standard annuity formula for German Annuitätendarlehen.

    Args:
        principal: Loan amount in EUR
        annual_rate: Annual interest rate (0.04 = 4%)
        years: Loan term in years
        payments_per_year: Number of payments per year (default 12 for monthly)

    Returns:
        Periodic payment amount in EUR

    Example:
        >>> calculate_annuity(300000, 0.04, 20)
        1817.94  # Monthly payment
    """
    if annual_rate <= 0:
        return principal / (years * payments_per_year)

    periodic_rate = annual_rate / payments_per_year
    n_payments = years * payments_per_year

    # Annuity formula: A = P * (r(1+r)^n) / ((1+r)^n - 1)
    annuity = principal * (periodic_rate * (1 + periodic_rate)**n_payments) / \
              ((1 + periodic_rate)**n_payments - 1)

    return round(annuity, 2)


def calculate_loan_balance(
    principal: float,
    annual_rate: float,
    years: int,
    payments_made: int,
    payments_per_year: int = 12
) -> float:
    """
    Calculate remaining loan balance after a number of payments.

    Args:
        principal: Original loan amount
        annual_rate: Annual interest rate
        years: Original loan term
        payments_made: Number of payments already made
        payments_per_year: Payments per year

    Returns:
        Remaining loan balance
    """
    if annual_rate <= 0:
        payment = principal / (years * payments_per_year)
        return max(0, principal - payment * payments_made)

    periodic_rate = annual_rate / payments_per_year
    n_payments = years * payments_per_year
    payment = calculate_annuity(principal, annual_rate, years, payments_per_year)

    # Remaining balance formula
    if payments_made >= n_payments:
        return 0

    balance = principal * (1 + periodic_rate)**payments_made - \
              payment * ((1 + periodic_rate)**payments_made - 1) / periodic_rate

    return max(0, round(balance, 2))


def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    years: int,
    extra_payment: float = 0,
    payments_per_year: int = 12
) -> List[Dict[str, Any]]:
    """
    Generate a full amortization schedule for a loan.

    Args:
        principal: Loan amount
        annual_rate: Annual interest rate
        years: Loan term
        extra_payment: Additional payment per period
        payments_per_year: Payments per year

    Returns:
        List of dictionaries with payment details per period
    """
    schedule = []
    balance = principal
    periodic_rate = annual_rate / payments_per_year
    payment = calculate_annuity(principal, annual_rate, years, payments_per_year)
    total_payment = payment + extra_payment

    period = 0
    year = 0
    total_interest = 0
    total_principal = 0

    while balance > 0.01:
        period += 1
        year = (period - 1) // payments_per_year + 1

        interest = balance * periodic_rate
        principal_payment = min(total_payment - interest, balance)
        balance -= principal_payment

        total_interest += interest
        total_principal += principal_payment

        schedule.append({
            "period": period,
            "year": year,
            "payment": round(total_payment, 2),
            "principal": round(principal_payment, 2),
            "interest": round(interest, 2),
            "balance": round(max(0, balance), 2),
            "total_interest": round(total_interest, 2),
            "total_principal": round(total_principal, 2),
        })

        if period > years * payments_per_year * 2:  # Safety limit
            break

    return schedule


def calculate_irr(cash_flows: List[float]) -> float:
    """
    Calculate Internal Rate of Return (IRR).

    Args:
        cash_flows: List of cash flows (first is typically negative - initial investment)

    Returns:
        IRR as decimal (0.10 = 10%)
    """
    try:
        irr = npf.irr(cash_flows)
        if np.isnan(irr):
            return 0.0
        return float(irr)
    except Exception:
        return 0.0


def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
    """
    Calculate Net Present Value (NPV).

    Correct NPV formula: CF₀ + Σ(CFₜ / (1+r)^t) for t=1 to n
    Period 0 is NOT discounted (it represents today's value).

    Args:
        cash_flows: List of cash flows (cash_flows[0] is period 0, typically negative)
        discount_rate: Discount rate as decimal (0.08 = 8%)

    Returns:
        NPV in same currency as cash flows

    Example:
        >>> calculate_npv([-100000, 20000, 25000, 30000, 120000], 0.08)
        # Period 0: -100000 (not discounted)
        # Period 1: 20000 / 1.08 = 18518.52
        # Period 2: 25000 / 1.08² = 21433.47
        # etc.
    """
    if not cash_flows:
        return 0.0

    # Period 0 is NOT discounted (it's today's value)
    npv = float(cash_flows[0])

    for t, cf in enumerate(cash_flows[1:], start=1):
        npv += cf / ((1 + discount_rate) ** t)

    return round(npv, 2)


def calculate_equity_multiple(total_returns: float, total_invested: float) -> float:
    """
    Calculate equity multiple (total return / total invested).

    Args:
        total_returns: Sum of all returns including exit
        total_invested: Total capital invested

    Returns:
        Equity multiple (e.g., 1.5x means 50% total return)
    """
    if total_invested == 0:
        return 0
    return total_returns / total_invested


def calculate_cash_on_cash(annual_cash_flow: float, total_equity: float) -> float:
    """
    Calculate cash-on-cash return.

    Args:
        annual_cash_flow: Annual pre-tax cash flow
        total_equity: Total equity invested

    Returns:
        Cash-on-cash return as decimal
    """
    if total_equity == 0:
        return 0
    return annual_cash_flow / total_equity


def calculate_dscr(noi: float, debt_service: float) -> float:
    """
    Calculate Debt Service Coverage Ratio.

    Args:
        noi: Net Operating Income
        debt_service: Annual debt service (mortgage payments)

    Returns:
        DSCR ratio (healthy > 1.2)
    """
    if debt_service == 0:
        return float('inf')
    return noi / debt_service


def calculate_price_to_rent_ratio(
    purchase_price: float,
    annual_rent: float
) -> float:
    """
    Calculate price-to-rent ratio.

    Historical German mean: 20-25x
    Warning: >30x
    Crisis: >35x

    Args:
        purchase_price: Property purchase price in EUR
        annual_rent: Annual rental income in EUR (gross)

    Returns:
        Price-to-rent ratio (number of years of rent to equal price)
    """
    if annual_rent == 0:
        return float('inf')
    return purchase_price / annual_rent


def calculate_price_to_income_ratio(
    median_home_price: float,
    median_household_income: float
) -> float:
    """
    Calculate price-to-income ratio.

    Historical German mean: 5.5-6.0
    Warning: >7.5
    Crisis: >9.0

    Args:
        median_home_price: Median home price in city
        median_household_income: Median annual household income

    Returns:
        Price-to-income ratio
    """
    if median_household_income == 0:
        return float('inf')
    return median_home_price / median_household_income


def calculate_rental_yield(
    annual_rent: float,
    purchase_price: float,
    gross: bool = True
) -> float:
    """
    Calculate rental yield (Mietrendite).

    Args:
        annual_rent: Annual rental income
        purchase_price: Property purchase price
        gross: If True, calculate gross yield; if False, net yield

    Returns:
        Yield as decimal (0.05 = 5%)
    """
    if purchase_price == 0:
        return 0
    return annual_rent / purchase_price


def estimate_renovation_cost(
    sqm: float,
    property_age: int,
    last_renovation_year: Optional[int],
    condition: str = "normal"
) -> Dict[str, float]:
    """
    Estimate renovation costs based on property characteristics.

    Args:
        sqm: Property size in square meters
        property_age: Age of the property in years
        last_renovation_year: Year of last renovation (None if never renovated)
        condition: "good", "normal", "poor"

    Returns:
        Dictionary with estimated costs:
        - immediate: Required now
        - 5_year: Expected in next 5 years
        - 10_year: Expected in next 10 years
        - reserve: Recommended annual reserve
    """
    base_cost_per_sqm = {
        "good": 100,
        "normal": 300,
        "poor": 800
    }.get(condition, 300)

    # Adjust for age
    age_factor = 1.0
    if property_age > 50:
        age_factor = 1.5
    elif property_age > 30:
        age_factor = 1.2

    # Adjust for last renovation
    years_since_renovation = 0
    if last_renovation_year:
        years_since_renovation = datetime.now().year - last_renovation_year
    else:
        years_since_renovation = min(property_age, 30)

    renovation_factor = 1 + (years_since_renovation / 30)

    immediate = sqm * base_cost_per_sqm * age_factor * renovation_factor
    five_year = sqm * 150 * age_factor
    ten_year = sqm * 300 * age_factor

    # Annual reserve recommendation (1% of value or calculated need)
    annual_reserve = (immediate + five_year + ten_year) / 10

    return {
        "immediate": round(immediate, 2),
        "5_year": round(five_year, 2),
        "10_year": round(ten_year, 2),
        "annual_reserve": round(annual_reserve, 2),
    }


def calculate_energy_cost_factor(heating_type: str, energy_class: str) -> float:
    """
    Calculate energy cost factor based on heating and efficiency.

    Args:
        heating_type: Type of heating system
        energy_class: Energy efficiency class (A+ to H)

    Returns:
        Factor to multiply base energy costs (1.0 = average)
    """
    heating_factors = {
        "Wärmepumpe": 0.6,
        "Fernwärme": 0.9,
        "Gas": 1.0,
        "Pellet": 0.8,
        "Öl": 1.3,
        "Elektro": 1.5,
    }

    energy_factors = {
        "A+": 0.5,
        "A": 0.6,
        "B": 0.7,
        "C": 0.85,
        "D": 1.0,
        "E": 1.2,
        "F": 1.4,
        "G": 1.6,
        "H": 1.8,
    }

    h_factor = heating_factors.get(heating_type, 1.0)
    e_factor = energy_factors.get(energy_class, 1.0)

    return h_factor * e_factor


def years_to_date(years: float, from_date: Optional[date] = None) -> date:
    """Convert years to a future date."""
    if from_date is None:
        from_date = date.today()
    days = int(years * 365.25)
    return from_date.replace(day=1) + timedelta(days=days)


def date_to_years(target_date: date, from_date: Optional[date] = None) -> float:
    """Convert a date to years from now."""
    if from_date is None:
        from_date = date.today()
    delta = target_date - from_date
    return delta.days / 365.25


def basis_points_to_decimal(bps: int) -> float:
    """Convert basis points to decimal (100 bps = 0.01 = 1%)."""
    return bps / 10000


def decimal_to_basis_points(rate: float) -> int:
    """Convert decimal rate to basis points."""
    return int(round(rate * 10000))


# Import timedelta for date calculations
from datetime import timedelta
