"""
German Real Estate Tax Calculator.

Implements accurate German tax calculations for real estate investments:
- Grunderwerbsteuer (property transfer tax) by Bundesland
- AfA (depreciation) rates based on building age
- Capital gains tax with Spekulationsfrist
- Income tax calculations with Solidaritätszuschlag and Kirchensteuer
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime


# Grunderwerbsteuer rates by Bundesland (as of 2024)
GRUNDERWERBSTEUER_RATES: Dict[str, float] = {
    "Baden-Württemberg": 0.05,
    "Bayern": 0.035,
    "Berlin": 0.06,
    "Brandenburg": 0.065,
    "Bremen": 0.05,
    "Hamburg": 0.055,
    "Hessen": 0.06,
    "Mecklenburg-Vorpommern": 0.06,
    "Niedersachsen": 0.05,
    "Nordrhein-Westfalen": 0.065,
    "Rheinland-Pfalz": 0.05,
    "Saarland": 0.065,
    "Sachsen": 0.055,
    "Sachsen-Anhalt": 0.05,
    "Schleswig-Holstein": 0.065,
    "Thüringen": 0.065,
}

# Kirchensteuer rates by Bundesland
KIRCHENSTEUER_RATES: Dict[str, float] = {
    "Baden-Württemberg": 0.08,
    "Bayern": 0.08,
    # All other Bundesländer: 9%
}


@dataclass
class AcquisitionCosts:
    """Breakdown of property acquisition costs."""
    purchase_price: float
    grunderwerbsteuer: float
    grunderwerbsteuer_rate: float
    notar_fees: float  # ~1.5% of purchase price
    grundbuch_fees: float  # ~0.5% of purchase price
    makler_fees: float  # Typically 3.57% (3% + VAT) buyer's share
    total_acquisition_cost: float
    acquisition_cost_percentage: float


@dataclass
class DepreciationSchedule:
    """AfA depreciation schedule for a property."""
    building_value: float
    land_value_ratio: float
    depreciable_base: float
    annual_rate: float
    annual_amount: float
    total_years: int
    baujahr: int
    afa_type: str  # "Linear 2%", "Linear 2.5%", "Linear 3%"


@dataclass
class CapitalGainsTax:
    """Capital gains tax calculation result."""
    sale_price: float
    original_cost_basis: float
    accumulated_depreciation: float
    adjusted_cost_basis: float
    capital_gain: float
    holding_period_years: int
    is_tax_exempt: bool  # True if held > 10 years
    taxable_gain: float
    estimated_tax: float
    effective_rate: float


def get_grunderwerbsteuer_rate(bundesland: str) -> float:
    """
    Get the Grunderwerbsteuer rate for a Bundesland.

    Args:
        bundesland: Name of the German Bundesland

    Returns:
        Tax rate as decimal (e.g., 0.05 for 5%)
    """
    return GRUNDERWERBSTEUER_RATES.get(bundesland, 0.05)  # Default to 5%


def get_kirchensteuer_rate(bundesland: str) -> float:
    """
    Get the Kirchensteuer rate for a Bundesland.

    Args:
        bundesland: Name of the German Bundesland

    Returns:
        Tax rate as decimal (0.08 for BY/BW, 0.09 for others)
    """
    return KIRCHENSTEUER_RATES.get(bundesland, 0.09)


def get_depreciation_rate(baujahr: int) -> Tuple[float, int, str]:
    """
    Get the AfA depreciation rate based on construction year.

    German depreciation rules:
    - Buildings completed before 1925: 2.5% over 40 years
    - Buildings completed 1925-2022: 2% over 50 years
    - Buildings completed 2023+: 3% over 33.33 years (JStG 2022)

    Args:
        baujahr: Year of construction

    Returns:
        Tuple of (annual_rate, total_years, description)
    """
    if baujahr < 1925:
        return (0.025, 40, "Linear 2,5% (vor 1925)")
    elif baujahr <= 2022:
        return (0.02, 50, "Linear 2% (1925-2022)")
    else:
        return (0.03, 34, "Linear 3% (ab 2023, JStG 2022)")


def calculate_acquisition_costs(
    purchase_price: float,
    bundesland: str,
    include_makler: bool = True,
    makler_rate: float = 0.0357  # 3% + 19% VAT = 3.57%
) -> AcquisitionCosts:
    """
    Calculate total acquisition costs for a property purchase.

    Args:
        purchase_price: Property purchase price in EUR
        bundesland: German Bundesland for tax calculation
        include_makler: Whether to include broker fees
        makler_rate: Broker fee rate (default 3.57% = 3% + VAT)

    Returns:
        AcquisitionCosts breakdown
    """
    # Grunderwerbsteuer
    gst_rate = get_grunderwerbsteuer_rate(bundesland)
    grunderwerbsteuer = purchase_price * gst_rate

    # Notar fees (~1.5% of purchase price)
    notar_fees = purchase_price * 0.015

    # Grundbuch (land registry) fees (~0.5% of purchase price)
    grundbuch_fees = purchase_price * 0.005

    # Makler fees (if applicable)
    makler_fees = purchase_price * makler_rate if include_makler else 0

    # Total
    total = purchase_price + grunderwerbsteuer + notar_fees + grundbuch_fees + makler_fees
    percentage = (total - purchase_price) / purchase_price

    return AcquisitionCosts(
        purchase_price=purchase_price,
        grunderwerbsteuer=grunderwerbsteuer,
        grunderwerbsteuer_rate=gst_rate,
        notar_fees=notar_fees,
        grundbuch_fees=grundbuch_fees,
        makler_fees=makler_fees,
        total_acquisition_cost=total,
        acquisition_cost_percentage=percentage,
    )


def calculate_depreciation_schedule(
    purchase_price: float,
    baujahr: int,
    land_value_ratio: float = 0.20  # Typically 15-25% of value is land
) -> DepreciationSchedule:
    """
    Calculate AfA depreciation schedule for a property.

    Only the building value (not land) can be depreciated.

    Args:
        purchase_price: Total property purchase price in EUR
        baujahr: Year of construction
        land_value_ratio: Portion of value attributable to land (not depreciable)

    Returns:
        DepreciationSchedule with annual amounts
    """
    # Only building value is depreciable
    building_value = purchase_price * (1 - land_value_ratio)

    # Get appropriate depreciation rate
    annual_rate, total_years, afa_type = get_depreciation_rate(baujahr)

    # Calculate annual depreciation amount
    annual_amount = building_value * annual_rate

    return DepreciationSchedule(
        building_value=purchase_price,
        land_value_ratio=land_value_ratio,
        depreciable_base=building_value,
        annual_rate=annual_rate,
        annual_amount=annual_amount,
        total_years=total_years,
        baujahr=baujahr,
        afa_type=afa_type,
    )


def calculate_capital_gains_tax(
    sale_price: float,
    original_cost_basis: float,
    accumulated_depreciation: float,
    holding_period_years: int,
    marginal_tax_rate: float = 0.42,
    bundesland: str = "Bayern",
    is_church_member: bool = False
) -> CapitalGainsTax:
    """
    Calculate capital gains tax on property sale.

    German Spekulationsfrist: If property is held for more than 10 years,
    the capital gain is tax-exempt (for private investors).

    Args:
        sale_price: Property sale price in EUR
        original_cost_basis: Original acquisition cost (including Nebenkosten)
        accumulated_depreciation: Total AfA claimed over holding period
        holding_period_years: Years the property was held
        marginal_tax_rate: Investor's marginal income tax rate
        bundesland: Bundesland for Kirchensteuer rate
        is_church_member: Whether to apply Kirchensteuer

    Returns:
        CapitalGainsTax calculation
    """
    # Adjusted cost basis (reduced by depreciation claimed)
    adjusted_cost_basis = original_cost_basis - accumulated_depreciation

    # Calculate gain
    capital_gain = sale_price - adjusted_cost_basis

    # Check Spekulationsfrist (10-year holding period)
    is_tax_exempt = holding_period_years >= 10

    if is_tax_exempt or capital_gain <= 0:
        taxable_gain = 0
        estimated_tax = 0
        effective_rate = 0
    else:
        taxable_gain = capital_gain

        # Calculate tax with Solidaritätszuschlag and optional Kirchensteuer
        soli_rate = 0.055  # 5.5% Solidaritätszuschlag

        if is_church_member:
            kirchen_rate = get_kirchensteuer_rate(bundesland)
        else:
            kirchen_rate = 0

        # Total effective rate
        effective_rate = marginal_tax_rate * (1 + soli_rate + kirchen_rate)
        estimated_tax = taxable_gain * effective_rate

    return CapitalGainsTax(
        sale_price=sale_price,
        original_cost_basis=original_cost_basis,
        accumulated_depreciation=accumulated_depreciation,
        adjusted_cost_basis=adjusted_cost_basis,
        capital_gain=capital_gain,
        holding_period_years=holding_period_years,
        is_tax_exempt=is_tax_exempt,
        taxable_gain=taxable_gain,
        estimated_tax=estimated_tax,
        effective_rate=effective_rate if taxable_gain > 0 else 0,
    )


def calculate_rental_income_tax(
    annual_rent: float,
    annual_depreciation: float,
    annual_interest: float,
    annual_operating_costs: float,
    marginal_tax_rate: float = 0.42,
    bundesland: str = "Bayern",
    is_church_member: bool = False
) -> Dict[str, float]:
    """
    Calculate income tax on rental income.

    Taxable rental income = Rent - Depreciation - Interest - Operating Costs

    Args:
        annual_rent: Gross annual rental income
        annual_depreciation: Annual AfA amount
        annual_interest: Annual mortgage interest
        annual_operating_costs: Non-recoverable operating costs
        marginal_tax_rate: Investor's marginal income tax rate
        bundesland: Bundesland for Kirchensteuer rate
        is_church_member: Whether to apply Kirchensteuer

    Returns:
        Dict with tax calculation breakdown
    """
    # Calculate taxable income
    taxable_income = annual_rent - annual_depreciation - annual_interest - annual_operating_costs

    # If negative, creates a loss that can offset other income
    if taxable_income <= 0:
        return {
            "gross_rent": annual_rent,
            "deductions": {
                "depreciation": annual_depreciation,
                "interest": annual_interest,
                "operating_costs": annual_operating_costs,
            },
            "taxable_income": taxable_income,
            "is_loss": True,
            "tax_savings": abs(taxable_income) * marginal_tax_rate,  # Approximate
            "effective_tax": 0,
        }

    # Calculate tax
    soli_rate = 0.055
    kirchen_rate = get_kirchensteuer_rate(bundesland) if is_church_member else 0

    base_tax = taxable_income * marginal_tax_rate
    soli = base_tax * soli_rate
    kirchen = base_tax * kirchen_rate

    total_tax = base_tax + soli + kirchen

    return {
        "gross_rent": annual_rent,
        "deductions": {
            "depreciation": annual_depreciation,
            "interest": annual_interest,
            "operating_costs": annual_operating_costs,
        },
        "taxable_income": taxable_income,
        "is_loss": False,
        "base_tax": base_tax,
        "solidaritaetszuschlag": soli,
        "kirchensteuer": kirchen,
        "total_tax": total_tax,
        "effective_rate": total_tax / annual_rent if annual_rent > 0 else 0,
    }


def get_all_bundeslaender() -> list:
    """Return a sorted list of all German Bundesländer."""
    return sorted(GRUNDERWERBSTEUER_RATES.keys())


def format_tax_summary(bundesland: str) -> str:
    """
    Format a summary of tax rates for a Bundesland.

    Args:
        bundesland: Name of the Bundesland

    Returns:
        Formatted string with tax information
    """
    gst = get_grunderwerbsteuer_rate(bundesland)
    kirchen = get_kirchensteuer_rate(bundesland)

    return f"""
Steuerübersicht {bundesland}:
- Grunderwerbsteuer: {gst:.1%}
- Kirchensteuer: {kirchen:.0%}
- Solidaritätszuschlag: 5,5%
- AfA (Neubau ab 2023): 3% linear
- AfA (Bestand): 2% linear
- Spekulationsfrist: 10 Jahre
"""
