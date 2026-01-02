"""
Discounted Cash Flow (DCF) Model for German Real Estate Investment Analysis.

Provides comprehensive financial modeling for property investments including:
- Full amortization schedule
- Cash flow projections
- NPV, IRR, and other return metrics
- Tax implications (German tax law)
- Scenario analysis (Bear/Base/Bull)
- Sensitivity analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from enum import Enum
import numpy as np
import numpy_financial as npf
import pandas as pd

from ..utils.config import config, PropertyType, HeatingType, EnergyClass
from ..utils.helpers import (
    calculate_annuity, generate_amortization_schedule,
    calculate_irr, calculate_npv, calculate_dscr,
    calculate_rental_yield, estimate_renovation_cost,
    calculate_energy_cost_factor, format_currency
)
from ..utils.plz_service import plz_service
from ..utils.german_tax import (
    get_grunderwerbsteuer_rate, get_depreciation_rate,
    calculate_acquisition_costs, calculate_capital_gains_tax,
    calculate_depreciation_schedule
)
from ..data_fetchers.market_data import market_data_fetcher


class Scenario(Enum):
    """Investment scenario types."""
    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


@dataclass
class PropertyInput:
    """Input parameters for property investment analysis."""
    # Property details
    purchase_price: float
    sqm: float
    property_type: str = "Wohnung"
    plz: str = ""
    city: str = ""

    # Building characteristics
    baujahr: int = 2000  # Year built
    last_renovation: Optional[int] = None
    heating_type: str = "Gas"
    energy_class: str = "D"
    condition: str = "normal"  # good, normal, renovierungsbedürftig

    # Financing
    ltv: float = 0.80  # Loan-to-value
    interest_rate: float = 0.038  # Annual interest rate
    loan_term_years: int = 20
    amortization_rate: float = 0.02  # Initial amortization rate

    # Operating assumptions
    initial_rent_sqm: Optional[float] = None  # Monthly rent per sqm
    vacancy_rate: float = 0.03  # 3%
    rent_growth_rate: float = 0.02  # Annual rent growth
    operating_expense_ratio: float = 0.20  # Of gross rent
    property_tax_rate: float = 0.01  # Grundsteuer as % of value
    maintenance_reserve_rate: float = 0.01  # Annual as % of value

    # Exit assumptions
    holding_period_years: int = 10
    exit_price_growth: float = 0.02  # Annual price appreciation
    selling_costs: float = 0.06  # Makler, Notar, etc.

    # Tax assumptions
    personal_tax_rate: float = 0.42  # Marginal tax rate
    depreciation_rate: float = 0.02  # Linear depreciation for residential
    land_value_ratio: float = 0.20  # Land portion (not depreciable)

    # Additional costs
    acquisition_costs: float = 0.10  # Grunderwerbsteuer, Notar, Makler
    initial_renovation: float = 0.0  # Immediate renovation costs


@dataclass
class CashFlowYear:
    """Cash flow breakdown for a single year."""
    year: int

    # Income
    gross_rental_income: float
    vacancy_loss: float
    effective_rental_income: float

    # Expenses
    operating_expenses: float
    property_tax: float
    maintenance_reserve: float
    total_expenses: float

    # NOI
    net_operating_income: float

    # Debt service
    interest_payment: float
    principal_payment: float
    total_debt_service: float

    # Before-tax cash flow
    before_tax_cash_flow: float

    # Tax calculation
    depreciation: float
    taxable_income: float
    income_tax: float

    # After-tax cash flow
    after_tax_cash_flow: float

    # Cumulative
    cumulative_cash_flow: float
    loan_balance: float
    equity_buildup: float


@dataclass
class InvestmentMetrics:
    """Key investment metrics."""
    # Return metrics
    irr_before_tax: float
    irr_after_tax: float
    npv: float
    equity_multiple: float
    cash_on_cash_year1: float
    average_cash_on_cash: float

    # Yield metrics
    gross_rental_yield: float
    net_rental_yield: float
    cap_rate: float

    # Risk metrics
    dscr_year1: float
    breakeven_occupancy: float
    payback_period: Optional[float]

    # Total returns
    total_profit: float
    total_return: float
    annualized_return: float


@dataclass
class ScenarioResult:
    """Results for a single scenario."""
    scenario: Scenario
    assumptions: Dict[str, float]
    cash_flows: List[CashFlowYear]
    metrics: InvestmentMetrics
    exit_analysis: Dict[str, float]


@dataclass
class DCFAnalysisResult:
    """Complete DCF analysis result."""
    property_input: PropertyInput
    base_case: ScenarioResult
    bear_case: Optional[ScenarioResult]
    bull_case: Optional[ScenarioResult]
    sensitivity_analysis: Dict[str, Any]
    summary: str
    recommendation: str
    analysis_date: datetime


class DCFModel:
    """
    Comprehensive DCF model for German real estate investments.

    Calculates all relevant financial metrics including German-specific
    tax implications and regulatory considerations.
    """

    def __init__(self):
        """Initialize DCF model."""
        self.config = config

    def analyze_investment(
        self,
        inputs: PropertyInput,
        include_scenarios: bool = True,
        include_sensitivity: bool = True
    ) -> DCFAnalysisResult:
        """
        Perform complete DCF analysis on a property investment.

        Args:
            inputs: Property and investment parameters
            include_scenarios: Calculate bear/bull scenarios
            include_sensitivity: Calculate sensitivity analysis

        Returns:
            Complete DCF analysis result
        """
        # Enrich inputs with market data if needed
        inputs = self._enrich_inputs(inputs)

        # Calculate base case
        base_case = self._calculate_scenario(inputs, Scenario.BASE)

        # Calculate alternative scenarios if requested
        bear_case = None
        bull_case = None

        if include_scenarios:
            bear_inputs = self._adjust_for_scenario(inputs, Scenario.BEAR)
            bear_case = self._calculate_scenario(bear_inputs, Scenario.BEAR)

            bull_inputs = self._adjust_for_scenario(inputs, Scenario.BULL)
            bull_case = self._calculate_scenario(bull_inputs, Scenario.BULL)

        # Calculate sensitivity analysis if requested
        sensitivity = {}
        if include_sensitivity:
            sensitivity = self._calculate_sensitivity(inputs)

        # Generate summary and recommendation
        summary = self._generate_summary(inputs, base_case, bear_case, bull_case)
        recommendation = self._generate_recommendation(base_case, bear_case)

        return DCFAnalysisResult(
            property_input=inputs,
            base_case=base_case,
            bear_case=bear_case,
            bull_case=bull_case,
            sensitivity_analysis=sensitivity,
            summary=summary,
            recommendation=recommendation,
            analysis_date=datetime.now()
        )

    def _enrich_inputs(self, inputs: PropertyInput) -> PropertyInput:
        """Enrich inputs with market data where not provided."""
        # Get Bundesland from PLZ for correct tax rates
        bundesland = None
        if inputs.plz:
            bundesland = plz_service.get_bundesland(inputs.plz)

        # Calculate correct acquisition costs using Bundesland-specific Grunderwerbsteuer
        if bundesland:
            acq_costs = calculate_acquisition_costs(
                inputs.purchase_price,
                bundesland,
                include_makler=True
            )
            # Update acquisition_costs as ratio of purchase price
            inputs.acquisition_costs = acq_costs.acquisition_cost_percentage

        # Get correct depreciation rate based on building year (JStG 2022)
        afa_rate, _, _ = get_depreciation_rate(inputs.baujahr)
        inputs.depreciation_rate = afa_rate

        # Get rent estimate from market data if not provided
        if inputs.initial_rent_sqm is None:
            if inputs.plz:
                # Try PLZ service first for more accurate data
                market_data = plz_service.interpolate_market_data(inputs.plz)
                if market_data:
                    inputs.initial_rent_sqm = market_data["rent_sqm"]
                else:
                    # Fallback to market data fetcher
                    rental_data = market_data_fetcher.get_rental_estimate(
                        inputs.plz,
                        inputs.sqm,
                        inputs.property_type,
                        inputs.condition
                    )
                    inputs.initial_rent_sqm = rental_data.get("rent_per_sqm", 12.0)
            else:
                # Default rent estimate
                inputs.initial_rent_sqm = 12.0

        # Estimate renovation costs if renovierungsbedürftig
        if inputs.condition == "renovierungsbedürftig" and inputs.initial_renovation == 0:
            age = datetime.now().year - inputs.baujahr
            renovation = estimate_renovation_cost(
                inputs.sqm, age, inputs.last_renovation, inputs.condition
            )
            inputs.initial_renovation = renovation["immediate"]

        return inputs

    def _adjust_for_scenario(
        self,
        inputs: PropertyInput,
        scenario: Scenario
    ) -> PropertyInput:
        """Create adjusted inputs for bear/bull scenarios."""
        import copy
        adjusted = copy.deepcopy(inputs)

        if scenario == Scenario.BEAR:
            # Bear case: higher rates, lower rents, price decline
            adjusted.interest_rate = inputs.interest_rate + 0.01  # +100 bps
            adjusted.rent_growth_rate = 0.01  # 1% instead of 2%
            adjusted.exit_price_growth = -0.02  # -2% per year
            adjusted.vacancy_rate = 0.05  # 5% instead of 3%

        elif scenario == Scenario.BULL:
            # Bull case: lower rates, higher growth
            adjusted.interest_rate = max(0.02, inputs.interest_rate - 0.01)  # -100 bps
            adjusted.rent_growth_rate = 0.03  # 3%
            adjusted.exit_price_growth = 0.04  # 4% per year
            adjusted.vacancy_rate = 0.02  # 2%

        return adjusted

    def _calculate_scenario(
        self,
        inputs: PropertyInput,
        scenario: Scenario
    ) -> ScenarioResult:
        """Calculate complete cash flow for a scenario."""
        # Initial calculations
        loan_amount = inputs.purchase_price * inputs.ltv
        equity_invested = inputs.purchase_price * (1 - inputs.ltv)
        total_acquisition_cost = inputs.purchase_price * inputs.acquisition_costs
        initial_equity = equity_invested + total_acquisition_cost + inputs.initial_renovation

        # Generate cash flows for each year
        cash_flows = []
        cumulative_cf = -initial_equity
        loan_balance = loan_amount

        annual_rent = inputs.initial_rent_sqm * inputs.sqm * 12
        depreciable_value = inputs.purchase_price * (1 - inputs.land_value_ratio)
        annual_depreciation = depreciable_value * inputs.depreciation_rate

        all_cash_flows = [-initial_equity]  # Year 0

        for year in range(1, inputs.holding_period_years + 1):
            # Revenue calculations
            rent_multiplier = (1 + inputs.rent_growth_rate) ** (year - 1)
            gross_rent = annual_rent * rent_multiplier
            vacancy_loss = gross_rent * inputs.vacancy_rate
            effective_rent = gross_rent - vacancy_loss

            # Operating expenses
            operating_expenses = gross_rent * inputs.operating_expense_ratio
            property_tax = inputs.purchase_price * inputs.property_tax_rate
            maintenance = inputs.purchase_price * inputs.maintenance_reserve_rate
            total_expenses = operating_expenses + property_tax + maintenance

            # NOI
            noi = effective_rent - total_expenses

            # Debt service
            annual_payment = calculate_annuity(
                loan_amount, inputs.interest_rate, inputs.loan_term_years
            ) * 12

            # Calculate interest and principal for this year
            interest_paid = 0
            principal_paid = 0
            temp_balance = loan_balance

            for month in range(12):
                monthly_interest = temp_balance * inputs.interest_rate / 12
                monthly_principal = min(
                    annual_payment / 12 - monthly_interest,
                    temp_balance
                )
                interest_paid += monthly_interest
                principal_paid += monthly_principal
                temp_balance -= monthly_principal

            loan_balance = temp_balance

            # Before-tax cash flow
            btcf = noi - interest_paid - principal_paid

            # Tax calculation
            taxable_income = noi - interest_paid - annual_depreciation
            income_tax = max(0, taxable_income * inputs.personal_tax_rate)

            # After-tax cash flow
            atcf = btcf - income_tax

            cumulative_cf += atcf

            cf = CashFlowYear(
                year=year,
                gross_rental_income=gross_rent,
                vacancy_loss=vacancy_loss,
                effective_rental_income=effective_rent,
                operating_expenses=operating_expenses,
                property_tax=property_tax,
                maintenance_reserve=maintenance,
                total_expenses=total_expenses,
                net_operating_income=noi,
                interest_payment=interest_paid,
                principal_payment=principal_paid,
                total_debt_service=interest_paid + principal_paid,
                before_tax_cash_flow=btcf,
                depreciation=annual_depreciation,
                taxable_income=taxable_income,
                income_tax=income_tax,
                after_tax_cash_flow=atcf,
                cumulative_cash_flow=cumulative_cf,
                loan_balance=loan_balance,
                equity_buildup=initial_equity + principal_paid + cumulative_cf
            )

            cash_flows.append(cf)
            all_cash_flows.append(atcf)

        # Exit calculation
        exit_analysis = self._calculate_exit(inputs, cash_flows[-1])
        terminal_cf = exit_analysis["net_proceeds"]
        all_cash_flows[-1] += terminal_cf

        # Calculate metrics
        metrics = self._calculate_metrics(
            inputs, initial_equity, cash_flows, all_cash_flows, exit_analysis
        )

        # Scenario assumptions for documentation
        assumptions = {
            "interest_rate": inputs.interest_rate,
            "rent_growth": inputs.rent_growth_rate,
            "price_growth": inputs.exit_price_growth,
            "vacancy_rate": inputs.vacancy_rate
        }

        return ScenarioResult(
            scenario=scenario,
            assumptions=assumptions,
            cash_flows=cash_flows,
            metrics=metrics,
            exit_analysis=exit_analysis
        )

    def _calculate_exit(
        self,
        inputs: PropertyInput,
        final_cf: CashFlowYear
    ) -> Dict[str, float]:
        """Calculate exit/sale proceeds with German tax law (Spekulationsfrist)."""
        # Exit price based on growth assumption
        exit_price = inputs.purchase_price * (
            (1 + inputs.exit_price_growth) ** inputs.holding_period_years
        )

        # Selling costs
        selling_costs = exit_price * inputs.selling_costs

        # Remaining loan balance
        loan_payoff = final_cf.loan_balance

        # Calculate accumulated depreciation
        depreciable_value = inputs.purchase_price * (1 - inputs.land_value_ratio)
        accumulated_depreciation = depreciable_value * inputs.depreciation_rate * inputs.holding_period_years

        # Original cost basis (purchase price + acquisition costs)
        original_cost_basis = inputs.purchase_price * (1 + inputs.acquisition_costs)

        # Get Bundesland for tax calculation
        bundesland = "Bayern"  # Default
        if inputs.plz:
            bundesland = plz_service.get_bundesland(inputs.plz) or "Bayern"

        # Use proper German capital gains tax calculation with Spekulationsfrist
        cgt_result = calculate_capital_gains_tax(
            sale_price=exit_price,
            original_cost_basis=original_cost_basis,
            accumulated_depreciation=accumulated_depreciation,
            holding_period_years=inputs.holding_period_years,
            marginal_tax_rate=inputs.personal_tax_rate,
            bundesland=bundesland,
            is_church_member=False  # Conservative assumption
        )

        # Net proceeds
        gross_proceeds = exit_price - selling_costs
        net_proceeds = gross_proceeds - loan_payoff - cgt_result.estimated_tax

        return {
            "exit_price": exit_price,
            "selling_costs": selling_costs,
            "loan_payoff": loan_payoff,
            "capital_gain": cgt_result.capital_gain,
            "capital_gains_tax": cgt_result.estimated_tax,
            "is_tax_exempt": cgt_result.is_tax_exempt,
            "accumulated_depreciation": accumulated_depreciation,
            "gross_proceeds": gross_proceeds,
            "net_proceeds": net_proceeds
        }

    def _calculate_metrics(
        self,
        inputs: PropertyInput,
        initial_equity: float,
        cash_flows: List[CashFlowYear],
        all_cash_flows: List[float],
        exit_analysis: Dict[str, float]
    ) -> InvestmentMetrics:
        """Calculate all investment metrics."""
        # IRR calculations
        irr_after_tax = calculate_irr(all_cash_flows)

        # Before-tax cash flows for before-tax IRR
        bt_cash_flows = [-initial_equity]
        for cf in cash_flows:
            bt_cash_flows.append(cf.before_tax_cash_flow)
        bt_cash_flows[-1] += exit_analysis["net_proceeds"] + cash_flows[-1].income_tax
        irr_before_tax = calculate_irr(bt_cash_flows)

        # NPV at hurdle rate (e.g., 8%)
        hurdle_rate = 0.08
        npv = calculate_npv(all_cash_flows, hurdle_rate)

        # Total profit and returns
        total_at_cash_flow = sum(cf.after_tax_cash_flow for cf in cash_flows)
        total_profit = total_at_cash_flow + exit_analysis["net_proceeds"] - initial_equity
        total_return = total_profit / initial_equity if initial_equity > 0 else 0

        # Equity multiple
        total_distributions = total_at_cash_flow + exit_analysis["net_proceeds"]
        equity_multiple = total_distributions / initial_equity if initial_equity > 0 else 0

        # Cash-on-cash
        year1_coc = cash_flows[0].after_tax_cash_flow / initial_equity if initial_equity > 0 else 0
        avg_coc = np.mean([cf.after_tax_cash_flow / initial_equity for cf in cash_flows]) if initial_equity > 0 else 0

        # Yield metrics
        annual_rent = inputs.initial_rent_sqm * inputs.sqm * 12
        gross_yield = annual_rent / inputs.purchase_price
        net_yield = cash_flows[0].net_operating_income / inputs.purchase_price
        cap_rate = net_yield  # Simplified

        # Risk metrics
        dscr_y1 = calculate_dscr(
            cash_flows[0].net_operating_income,
            cash_flows[0].total_debt_service
        )

        # Breakeven occupancy
        total_fixed_costs = (
            cash_flows[0].operating_expenses +
            cash_flows[0].property_tax +
            cash_flows[0].total_debt_service
        )
        breakeven_occupancy = total_fixed_costs / cash_flows[0].gross_rental_income

        # Payback period
        cumulative = 0
        payback = None
        for i, cf in enumerate(cash_flows):
            cumulative += cf.after_tax_cash_flow
            if cumulative >= initial_equity and payback is None:
                # Linear interpolation
                prev_cum = cumulative - cf.after_tax_cash_flow
                remaining = initial_equity - prev_cum
                fraction = remaining / cf.after_tax_cash_flow
                payback = i + fraction

        # Add exit proceeds consideration for payback
        if payback is None:
            cumulative += exit_analysis["net_proceeds"]
            if cumulative >= initial_equity:
                payback = inputs.holding_period_years

        # Annualized return
        annualized_return = (1 + total_return) ** (1 / inputs.holding_period_years) - 1

        return InvestmentMetrics(
            irr_before_tax=irr_before_tax,
            irr_after_tax=irr_after_tax,
            npv=npv,
            equity_multiple=equity_multiple,
            cash_on_cash_year1=year1_coc,
            average_cash_on_cash=avg_coc,
            gross_rental_yield=gross_yield,
            net_rental_yield=net_yield,
            cap_rate=cap_rate,
            dscr_year1=dscr_y1,
            breakeven_occupancy=breakeven_occupancy,
            payback_period=payback,
            total_profit=total_profit,
            total_return=total_return,
            annualized_return=annualized_return
        )

    def _calculate_sensitivity(
        self,
        inputs: PropertyInput
    ) -> Dict[str, Any]:
        """
        Calculate sensitivity of IRR to key variables.

        Returns tornado chart data.
        """
        base_result = self._calculate_scenario(inputs, Scenario.BASE)
        base_irr = base_result.metrics.irr_after_tax

        sensitivities = {}

        # Variables to test with +/- ranges
        variables = {
            "purchase_price": (-0.15, 0.15, inputs.purchase_price),
            "interest_rate": (-0.015, 0.015, inputs.interest_rate),
            "initial_rent": (-0.15, 0.15, inputs.initial_rent_sqm),
            "vacancy_rate": (-0.02, 0.05, inputs.vacancy_rate),
            "exit_growth": (-0.03, 0.03, inputs.exit_price_growth),
        }

        import copy

        for var_name, (low_delta, high_delta, base_value) in variables.items():
            results = []

            for delta in [low_delta, high_delta]:
                test_inputs = copy.deepcopy(inputs)

                if var_name == "purchase_price":
                    test_inputs.purchase_price = base_value * (1 + delta)
                elif var_name == "interest_rate":
                    test_inputs.interest_rate = max(0.01, base_value + delta)
                elif var_name == "initial_rent":
                    test_inputs.initial_rent_sqm = base_value * (1 + delta)
                elif var_name == "vacancy_rate":
                    test_inputs.vacancy_rate = max(0, min(0.20, base_value + delta))
                elif var_name == "exit_growth":
                    test_inputs.exit_price_growth = base_value + delta

                test_result = self._calculate_scenario(test_inputs, Scenario.BASE)
                results.append(test_result.metrics.irr_after_tax)

            sensitivities[var_name] = {
                "base_irr": base_irr,
                "low_irr": results[0],
                "high_irr": results[1],
                "low_delta": low_delta,
                "high_delta": high_delta,
                "impact_range": abs(results[1] - results[0])
            }

        # Sort by impact
        sensitivities = dict(sorted(
            sensitivities.items(),
            key=lambda x: x[1]["impact_range"],
            reverse=True
        ))

        return sensitivities

    def _generate_summary(
        self,
        inputs: PropertyInput,
        base: ScenarioResult,
        bear: Optional[ScenarioResult],
        bull: Optional[ScenarioResult]
    ) -> str:
        """Generate human-readable investment summary."""
        m = base.metrics

        summary = f"""
## Investment Summary

**Property:** {inputs.sqm:.0f} qm {inputs.property_type} in {inputs.city or inputs.plz or 'Deutschland'}
**Purchase Price:** {format_currency(inputs.purchase_price)}
**Equity Required:** {format_currency(inputs.purchase_price * (1 - inputs.ltv) * (1 + inputs.acquisition_costs))}
**Holding Period:** {inputs.holding_period_years} Jahre

### Key Metrics (Base Case)
- **IRR (nach Steuern):** {m.irr_after_tax:.1%}
- **NPV (8% Hurdle):** {format_currency(m.npv)}
- **Equity Multiple:** {m.equity_multiple:.2f}x
- **Cash-on-Cash (Jahr 1):** {m.cash_on_cash_year1:.1%}
- **Brutto-Mietrendite:** {m.gross_rental_yield:.1%}
- **DSCR (Jahr 1):** {m.dscr_year1:.2f}

### Scenario Analysis
"""

        if bear:
            summary += f"- **Bear Case IRR:** {bear.metrics.irr_after_tax:.1%}\n"

        summary += f"- **Base Case IRR:** {m.irr_after_tax:.1%}\n"

        if bull:
            summary += f"- **Bull Case IRR:** {bull.metrics.irr_after_tax:.1%}\n"

        return summary

    def _generate_recommendation(
        self,
        base: ScenarioResult,
        bear: Optional[ScenarioResult]
    ) -> str:
        """Generate investment recommendation."""
        base_irr = base.metrics.irr_after_tax
        bear_irr = bear.metrics.irr_after_tax if bear else base_irr

        # Decision framework
        if base_irr >= 0.10 and bear_irr >= 0.05:
            return "STARKE EMPFEHLUNG - Attraktive Rendite selbst im pessimistischen Szenario"
        elif base_irr >= 0.08 and bear_irr >= 0.02:
            return "EMPFEHLUNG - Solide Rendite mit akzeptablem Downside-Risiko"
        elif base_irr >= 0.05 and bear_irr >= 0:
            return "NEUTRAL - Moderate Rendite, weiteres Research empfohlen"
        elif base_irr >= 0.03:
            return "VORSICHT - Geringe Rendite, nur bei strategischen Gründen sinnvoll"
        else:
            return "ABLEHNUNG - Unattraktive risikoadjustierte Rendite"


# Singleton instance
dcf_model = DCFModel()
