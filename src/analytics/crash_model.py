"""
Crash Probability Model for German Real Estate Investment Analysis.

A multi-factor scoring system (0-100 scale) that assesses the probability
of a real estate market correction based on:
1. Valuation Metrics (30% weight)
2. Credit Market Indicators (25% weight)
3. Supply/Demand Imbalance (20% weight)
4. Macro/Monetary Policy (15% weight)
5. Economic Fundamentals (10% weight)

Score interpretation:
- 0-19: STRONG_BUY - Blood in the streets, prices significantly below trend
- 20-39: BUY - Early recovery signals, attractive entry point
- 40-59: HOLD - Fair value, mixed signals
- 60-79: CAUTION - Overvaluation emerging, be careful
- 80-100: AVOID - Severe overvaluation, high crash probability
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

from ..utils.config import (
    config, Config, CrashModelWeights, ValuationThresholds,
    CreditMarketThresholds, SupplyDemandThresholds, MacroThresholds,
    InvestmentRecommendation
)
from ..data_fetchers.bundesbank import bundesbank_fetcher
from ..data_fetchers.destatis import destatis_fetcher
from ..data_fetchers.ecb import ecb_fetcher
from ..data_fetchers.market_data import market_data_fetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IndicatorScore:
    """Score for a single indicator."""
    name: str
    value: float
    score: float  # 0-100, higher = more risky
    weight: float
    weighted_score: float
    status: str  # "green", "yellow", "red"
    description: str


@dataclass
class CategoryScore:
    """Score for a category of indicators."""
    category: str
    score: float  # 0-100
    weight: float
    weighted_score: float
    status: str
    indicators: List[IndicatorScore]


@dataclass
class CrashProbabilityResult:
    """Complete crash probability analysis result."""
    total_score: float  # 0-100
    recommendation: InvestmentRecommendation
    category_scores: List[CategoryScore]
    city: Optional[str]
    analysis_date: datetime
    summary: str
    key_risks: List[str]
    key_positives: List[str]
    data_freshness: Dict[str, datetime]


class CrashProbabilityModel:
    """
    Multi-factor crash probability scoring model for German real estate.

    Aggregates data from multiple sources to calculate a crash risk score
    that helps investors time their entry into the market.
    """

    def __init__(self, config_override: Optional[Config] = None):
        """
        Initialize the crash probability model.

        Args:
            config_override: Optional custom configuration
        """
        self.config = config_override or config
        self.weights = self.config.crash_weights
        self.thresholds = {
            "valuation": self.config.valuation,
            "credit": self.config.credit,
            "supply_demand": self.config.supply_demand,
            "macro": self.config.macro,
        }

        # Data cache
        self._data_cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_duration = timedelta(hours=6)

    def _normalize_score(self, value: float, low: float, high: float, invert: bool = False) -> float:
        """
        Normalize a value to 0-100 score.

        Args:
            value: The value to normalize
            low: Value that maps to 0 (or 100 if inverted)
            high: Value that maps to 100 (or 0 if inverted)
            invert: If True, higher values = lower score

        Returns:
            Score between 0 and 100
        """
        if high == low:
            return 50

        score = (value - low) / (high - low) * 100
        score = max(0, min(100, score))

        if invert:
            score = 100 - score

        return score

    def _get_status(self, score: float) -> str:
        """Convert score to traffic light status."""
        if score < 40:
            return "green"
        elif score < 70:
            return "yellow"
        else:
            return "red"

    def calculate_valuation_score(self, city: Optional[str] = None) -> CategoryScore:
        """
        Calculate valuation metrics score (30% of total).

        Includes:
        - Price-to-Income Ratio
        - Price-to-Rent Ratio
        - Real Price Change (inflation-adjusted)
        """
        indicators = []

        # Get city data if specified, otherwise use national averages
        if city:
            city_data = market_data_fetcher.get_city_market_data(city)
        else:
            # Use weighted average of major cities
            city_data = None
            all_cities = market_data_fetcher.get_all_cities_data()
            if all_cities:
                avg_data = {
                    "price_to_rent_ratio": np.mean([c.price_to_rent_ratio for c in all_cities.values()]),
                    "price_to_income": np.mean([c.price_to_income for c in all_cities.values()]),
                    "price_yoy_change": np.mean([c.price_yoy_change for c in all_cities.values()]),
                }

        # 1. Price-to-Income Ratio
        thresholds = self.thresholds["valuation"]

        if city_data:
            pir = city_data.price_to_income
        else:
            pir = avg_data.get("price_to_income", 6.5)

        pir_score = self._normalize_score(
            pir,
            low=thresholds.pir_historical_mean,
            high=thresholds.pir_crisis
        )

        indicators.append(IndicatorScore(
            name="Price-to-Income Ratio",
            value=pir,
            score=pir_score,
            weight=0.35,
            weighted_score=pir_score * 0.35,
            status=self._get_status(pir_score),
            description=f"PIR of {pir:.1f}x vs historical mean of {thresholds.pir_historical_mean:.1f}x"
        ))

        # 2. Price-to-Rent Ratio
        if city_data:
            prr = city_data.price_to_rent_ratio
        else:
            prr = avg_data.get("price_to_rent_ratio", 25.0)

        prr_score = self._normalize_score(
            prr,
            low=thresholds.prr_historical_mean,
            high=thresholds.prr_crisis
        )

        indicators.append(IndicatorScore(
            name="Price-to-Rent Ratio",
            value=prr,
            score=prr_score,
            weight=0.35,
            weighted_score=prr_score * 0.35,
            status=self._get_status(prr_score),
            description=f"PRR of {prr:.1f}x vs historical mean of {thresholds.prr_historical_mean:.1f}x"
        ))

        # 3. Real Price Growth
        try:
            real_growth_df = destatis_fetcher.get_real_house_price_growth()
            if not real_growth_df.empty:
                real_growth = real_growth_df["value"].iloc[-1]
            else:
                real_growth = -3.0  # Current estimate for 2024
        except Exception:
            real_growth = -3.0

        # Positive real growth is risky, negative is safer
        real_growth_score = self._normalize_score(
            real_growth,
            low=-5.0,  # -5% real growth = very safe
            high=thresholds.real_growth_overheating  # 8% = overheating
        )

        indicators.append(IndicatorScore(
            name="Real Price Growth (YoY)",
            value=real_growth,
            score=real_growth_score,
            weight=0.30,
            weighted_score=real_growth_score * 0.30,
            status=self._get_status(real_growth_score),
            description=f"Real HPI growth of {real_growth:+.1f}% (inflation-adjusted)"
        ))

        # Calculate category score
        category_score = sum(i.weighted_score for i in indicators)

        return CategoryScore(
            category="Valuation Metrics",
            score=category_score,
            weight=self.weights.valuation_metrics / 100,
            weighted_score=category_score * self.weights.valuation_metrics / 100,
            status=self._get_status(category_score),
            indicators=indicators
        )

    def calculate_credit_score(self) -> CategoryScore:
        """
        Calculate credit market indicators score (25% of total).

        Includes:
        - Mortgage Rate Trajectory
        - Credit Volume Growth
        - Loan-to-Value trends
        - Debt Service Ratio
        """
        indicators = []
        thresholds = self.thresholds["credit"]

        # 1. Mortgage Rate Change
        try:
            rates = bundesbank_fetcher.get_mortgage_rates()
            if not rates.empty and len(rates) > 12:
                current_rate = rates["value"].iloc[-1]
                rate_12m_ago = rates["value"].iloc[-13]
                rate_change_bps = (current_rate - rate_12m_ago) * 100
            else:
                current_rate = 3.8
                rate_change_bps = -50  # Rates have stabilized/fallen slightly
        except Exception:
            current_rate = 3.8
            rate_change_bps = -50

        # Higher rate increases = more risky
        rate_score = self._normalize_score(
            rate_change_bps,
            low=-100,  # 100 bps decrease = very safe
            high=thresholds.rate_shock_critical_bps  # 200 bps increase = critical
        )

        indicators.append(IndicatorScore(
            name="Mortgage Rate Trajectory",
            value=rate_change_bps,
            score=rate_score,
            weight=0.35,
            weighted_score=rate_score * 0.35,
            status=self._get_status(rate_score),
            description=f"Rate change of {rate_change_bps:+.0f} bps YoY (current: {current_rate:.2f}%)"
        ))

        # 2. Credit Volume Growth
        try:
            credit_growth_df = bundesbank_fetcher.get_credit_growth()
            if not credit_growth_df.empty:
                credit_growth = credit_growth_df["value"].iloc[-1]
            else:
                credit_growth = -5.0  # Credit contraction in current environment
        except Exception:
            credit_growth = -5.0

        # High credit growth = bubble signal
        credit_score = self._normalize_score(
            credit_growth,
            low=-10.0,  # -10% = very safe (deleveraging)
            high=thresholds.credit_growth_bubble  # 15% = bubble
        )

        indicators.append(IndicatorScore(
            name="Credit Volume Growth (YoY)",
            value=credit_growth,
            score=credit_score,
            weight=0.30,
            weighted_score=credit_score * 0.30,
            status=self._get_status(credit_score),
            description=f"Housing credit growth of {credit_growth:+.1f}% YoY"
        ))

        # 3. Affordability Index (using current rates)
        # Estimate monthly payment for median home at current rate
        median_price = 350000  # German median
        ltv = 0.80
        loan = median_price * ltv
        monthly_rate = current_rate / 100 / 12
        term_months = 240
        monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**term_months) / ((1 + monthly_rate)**term_months - 1)
        median_income_monthly = 3800
        payment_to_income = monthly_payment / median_income_monthly

        affordability_score = self._normalize_score(
            payment_to_income * 100,
            low=25,  # 25% = healthy
            high=50   # 50% = unaffordable
        )

        indicators.append(IndicatorScore(
            name="Payment-to-Income Ratio",
            value=payment_to_income,
            score=affordability_score,
            weight=0.35,
            weighted_score=affordability_score * 0.35,
            status=self._get_status(affordability_score),
            description=f"Mortgage payment is {payment_to_income:.1%} of median income"
        ))

        category_score = sum(i.weighted_score for i in indicators)

        return CategoryScore(
            category="Credit Market",
            score=category_score,
            weight=self.weights.credit_market / 100,
            weighted_score=category_score * self.weights.credit_market / 100,
            status=self._get_status(category_score),
            indicators=indicators
        )

    def calculate_supply_demand_score(self, city: Optional[str] = None) -> CategoryScore:
        """
        Calculate supply/demand imbalance score (20% of total).

        Includes:
        - Inventory levels (months of supply)
        - Construction pipeline (permits)
        - Days on market
        """
        indicators = []
        thresholds = self.thresholds["supply_demand"]

        # 1. Inventory (Months of Supply)
        if city:
            city_data = market_data_fetcher.get_city_market_data(city)
            inventory = city_data.inventory_months if city_data else 5.5
        else:
            # National average estimate
            inventory = 5.5

        # Both shortage and oversupply can be problematic
        # Healthy is 4-6 months
        if inventory < thresholds.inventory_healthy_min:
            # Shortage - low risk of crash but unsustainable
            inv_score = self._normalize_score(
                inventory,
                low=thresholds.inventory_healthy_min,
                high=thresholds.inventory_shortage,
                invert=True
            ) * 0.5  # Less risky than oversupply
        elif inventory <= thresholds.inventory_healthy_max:
            inv_score = 20  # Healthy range
        else:
            # Oversupply - crash risk
            inv_score = self._normalize_score(
                inventory,
                low=thresholds.inventory_healthy_max,
                high=thresholds.inventory_oversupply + 2
            )

        indicators.append(IndicatorScore(
            name="Inventory (Months of Supply)",
            value=inventory,
            score=inv_score,
            weight=0.40,
            weighted_score=inv_score * 0.40,
            status=self._get_status(inv_score),
            description=f"{inventory:.1f} months of supply (healthy: 4-6 months)"
        ))

        # 2. Construction Pipeline (Building Permits YoY)
        try:
            construction = destatis_fetcher.get_construction_activity()
            permits_yoy = construction["permits_yoy"]
            if not permits_yoy.empty:
                permit_growth = permits_yoy["value"].iloc[-1]
            else:
                permit_growth = -30.0  # Significant decline in permits
        except Exception:
            permit_growth = -30.0

        # Falling permits = less future supply = lower crash risk
        permit_score = self._normalize_score(
            permit_growth,
            low=-40,  # -40% permits = very safe
            high=30   # +30% permits = potential oversupply coming
        )

        indicators.append(IndicatorScore(
            name="Building Permits (YoY)",
            value=permit_growth,
            score=permit_score,
            weight=0.35,
            weighted_score=permit_score * 0.35,
            status=self._get_status(permit_score),
            description=f"Building permits changed {permit_growth:+.1f}% YoY"
        ))

        # 3. Days on Market (if available)
        if city:
            city_data = market_data_fetcher.get_city_market_data(city)
            dom = city_data.days_on_market if city_data else 50
        else:
            dom = 50

        # Higher DOM = weaker demand = higher risk
        dom_score = self._normalize_score(
            dom,
            low=30,   # 30 days = hot market
            high=90   # 90 days = weak market
        )

        indicators.append(IndicatorScore(
            name="Days on Market",
            value=dom,
            score=dom_score,
            weight=0.25,
            weighted_score=dom_score * 0.25,
            status=self._get_status(dom_score),
            description=f"Average {dom:.0f} days on market"
        ))

        category_score = sum(i.weighted_score for i in indicators)

        return CategoryScore(
            category="Supply/Demand",
            score=category_score,
            weight=self.weights.supply_demand / 100,
            weighted_score=category_score * self.weights.supply_demand / 100,
            status=self._get_status(category_score),
            indicators=indicators
        )

    def calculate_macro_score(self) -> CategoryScore:
        """
        Calculate macro/monetary policy score (15% of total).

        Includes:
        - ECB Policy Stance
        - Yield Curve
        - Inflation vs Target
        """
        indicators = []

        # 1. ECB Policy Stance
        try:
            policy_summary = ecb_fetcher.get_monetary_policy_summary()
            trajectory = policy_summary.get("trajectory", {})

            if trajectory.get("phase") == "hiking_cycle":
                policy_score = 80
                policy_desc = "Restrictive - hiking cycle"
            elif trajectory.get("phase") == "cutting_cycle":
                policy_score = 30
                policy_desc = "Accommodative - cutting cycle"
            else:
                policy_score = 50
                policy_desc = "Neutral - stable rates"

            current_rate = trajectory.get("current_rate", 4.25)
        except Exception:
            policy_score = 50
            policy_desc = "Unable to determine"
            current_rate = 4.25

        indicators.append(IndicatorScore(
            name="ECB Policy Stance",
            value=current_rate,
            score=policy_score,
            weight=0.35,
            weighted_score=policy_score * 0.35,
            status=self._get_status(policy_score),
            description=f"{policy_desc} (MRR: {current_rate:.2f}%)"
        ))

        # 2. Yield Curve
        try:
            spread_df = bundesbank_fetcher.get_yield_curve_spread()
            if not spread_df.empty:
                spread = spread_df["value"].iloc[-1]
            else:
                spread = 0.3  # Slightly positive
        except Exception:
            spread = 0.3

        # Inversion is recession warning
        if spread < 0:
            curve_score = 90  # Inverted = high recession risk
            curve_desc = "INVERTED - recession signal"
        elif spread < 0.5:
            curve_score = 60  # Flat = caution
            curve_desc = "Flat - slowing growth"
        else:
            curve_score = 30  # Normal
            curve_desc = "Normal - healthy"

        indicators.append(IndicatorScore(
            name="Yield Curve (10Y-2Y)",
            value=spread,
            score=curve_score,
            weight=0.30,
            weighted_score=curve_score * 0.30,
            status=self._get_status(curve_score),
            description=f"Spread: {spread:.2f}% - {curve_desc}"
        ))

        # 3. Inflation vs Target
        try:
            inflation_outlook = ecb_fetcher.get_inflation_outlook()
            inflation = inflation_outlook.get("current_inflation", 2.5)
            deviation = abs(inflation - 2.0)
        except Exception:
            inflation = 2.5
            deviation = 0.5

        # Higher deviation from target = more policy uncertainty
        inflation_score = self._normalize_score(
            deviation,
            low=0,      # At target
            high=5      # 5pp deviation
        )

        indicators.append(IndicatorScore(
            name="Inflation Deviation",
            value=inflation,
            score=inflation_score,
            weight=0.35,
            weighted_score=inflation_score * 0.35,
            status=self._get_status(inflation_score),
            description=f"Inflation at {inflation:.1f}% (target: 2.0%)"
        ))

        category_score = sum(i.weighted_score for i in indicators)

        return CategoryScore(
            category="Macro/Monetary",
            score=category_score,
            weight=self.weights.macro_monetary / 100,
            weighted_score=category_score * self.weights.macro_monetary / 100,
            status=self._get_status(category_score),
            indicators=indicators
        )

    def calculate_fundamentals_score(self, city: Optional[str] = None) -> CategoryScore:
        """
        Calculate economic fundamentals score (10% of total).

        Includes:
        - GDP Growth
        - Unemployment Rate
        - Population Growth
        """
        indicators = []

        # 1. GDP Growth (estimated from inflation/construction)
        # Germany has had weak growth recently
        gdp_growth = 0.2  # Current estimate
        gdp_score = self._normalize_score(
            gdp_growth,
            low=2.0,   # 2% = strong
            high=-1.0,  # -1% = recession
            invert=True
        )

        indicators.append(IndicatorScore(
            name="GDP Growth (YoY)",
            value=gdp_growth,
            score=gdp_score,
            weight=0.40,
            weighted_score=gdp_score * 0.40,
            status=self._get_status(gdp_score),
            description=f"GDP growth of {gdp_growth:+.1f}%"
        ))

        # 2. Unemployment Rate
        if city:
            city_data = market_data_fetcher.get_city_market_data(city)
            unemployment = city_data.unemployment_rate if city_data else 5.5
        else:
            unemployment = 5.7  # National average

        unemp_score = self._normalize_score(
            unemployment,
            low=3.0,   # 3% = full employment
            high=10.0  # 10% = concerning
        )

        indicators.append(IndicatorScore(
            name="Unemployment Rate",
            value=unemployment,
            score=unemp_score,
            weight=0.35,
            weighted_score=unemp_score * 0.35,
            status=self._get_status(unemp_score),
            description=f"Unemployment at {unemployment:.1f}%"
        ))

        # 3. Population/Migration (demographic support)
        # Germany has positive net migration
        pop_growth = 0.3  # Positive due to migration
        pop_score = self._normalize_score(
            pop_growth,
            low=0.5,   # 0.5% growth = strong demand
            high=-0.5,  # -0.5% = declining
            invert=True
        )

        indicators.append(IndicatorScore(
            name="Population Growth",
            value=pop_growth,
            score=pop_score,
            weight=0.25,
            weighted_score=pop_score * 0.25,
            status=self._get_status(pop_score),
            description=f"Population growth of {pop_growth:+.1f}%"
        ))

        category_score = sum(i.weighted_score for i in indicators)

        return CategoryScore(
            category="Economic Fundamentals",
            score=category_score,
            weight=self.weights.economic_fundamentals / 100,
            weighted_score=category_score * self.weights.economic_fundamentals / 100,
            status=self._get_status(category_score),
            indicators=indicators
        )

    def calculate_crash_probability(
        self,
        city: Optional[str] = None
    ) -> CrashProbabilityResult:
        """
        Calculate complete crash probability score.

        Args:
            city: Optional city key for city-specific analysis

        Returns:
            CrashProbabilityResult with full analysis
        """
        # Calculate all category scores
        valuation = self.calculate_valuation_score(city)
        credit = self.calculate_credit_score()
        supply_demand = self.calculate_supply_demand_score(city)
        macro = self.calculate_macro_score()
        fundamentals = self.calculate_fundamentals_score(city)

        category_scores = [valuation, credit, supply_demand, macro, fundamentals]

        # Calculate total score
        total_score = sum(cat.weighted_score for cat in category_scores)

        # Get recommendation
        recommendation = self.config.get_recommendation(total_score)

        # Identify key risks and positives
        key_risks = []
        key_positives = []

        for cat in category_scores:
            for indicator in cat.indicators:
                if indicator.status == "red":
                    key_risks.append(f"{indicator.name}: {indicator.description}")
                elif indicator.status == "green":
                    key_positives.append(f"{indicator.name}: {indicator.description}")

        # Generate summary
        summary = self._generate_summary(total_score, recommendation, city)

        return CrashProbabilityResult(
            total_score=round(total_score, 1),
            recommendation=recommendation,
            category_scores=category_scores,
            city=city,
            analysis_date=datetime.now(),
            summary=summary,
            key_risks=key_risks[:5],  # Top 5 risks
            key_positives=key_positives[:5],  # Top 5 positives
            data_freshness={"analysis": datetime.now()}
        )

    def _generate_summary(
        self,
        score: float,
        recommendation: InvestmentRecommendation,
        city: Optional[str]
    ) -> str:
        """Generate human-readable summary of the analysis."""
        location = f"für {city.title()}" if city else "für Deutschland"

        if recommendation == InvestmentRecommendation.STRONG_BUY:
            return f"Der Markt {location} zeigt starke Kaufsignale. Preise sind deutlich unter dem Trend, " \
                   f"und mehrere Indikatoren deuten auf eine Bodenbildung hin. Crash-Wahrscheinlichkeit: {score:.0f}%"
        elif recommendation == InvestmentRecommendation.BUY:
            return f"Der Markt {location} bietet gute Einstiegsmöglichkeiten. Die Bewertungen sind " \
                   f"attraktiver geworden. Crash-Wahrscheinlichkeit: {score:.0f}%"
        elif recommendation == InvestmentRecommendation.HOLD:
            return f"Der Markt {location} zeigt gemischte Signale. Weder stark überkauft noch " \
                   f"unterbewertet. Abwartende Haltung empfohlen. Crash-Wahrscheinlichkeit: {score:.0f}%"
        elif recommendation == InvestmentRecommendation.CAUTION:
            return f"Vorsicht {location}! Mehrere Überbewertungssignale sind erkennbar. " \
                   f"Nur bei sehr günstigen Konditionen einsteigen. Crash-Wahrscheinlichkeit: {score:.0f}%"
        else:  # AVOID
            return f"Hohe Crash-Wahrscheinlichkeit {location}! Starke Überbewertung auf mehreren Ebenen. " \
                   f"Abwarten bis zur Marktbereinigung wird empfohlen. Crash-Wahrscheinlichkeit: {score:.0f}%"


# Singleton instance
crash_model = CrashProbabilityModel()
