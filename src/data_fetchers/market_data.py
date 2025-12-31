"""
Market Data Aggregator for German Real Estate Investment Analysis.

Aggregates data from multiple sources and provides city-level market data
including prices per square meter, rental yields, and market indicators.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import random

from ..utils.config import config, GERMAN_CITIES, PLZ_CITY_MAPPING, CityData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MarketIndicator:
    """A market indicator value with metadata."""
    value: float
    date: datetime
    source: str
    unit: str
    trend: Optional[str] = None  # "up", "down", "stable"
    yoy_change: Optional[float] = None


@dataclass
class CityMarketData:
    """Complete market data for a city."""
    city_name: str
    city_key: str
    date: datetime

    # Prices
    avg_price_sqm: float
    price_range_low: float
    price_range_high: float
    price_yoy_change: float

    # Rents
    avg_rent_sqm: float
    rent_yoy_change: float

    # Yields
    gross_rental_yield: float
    price_to_rent_ratio: float

    # Market health
    inventory_months: float
    days_on_market: float
    price_to_income: float

    # Demographics
    population: int
    unemployment_rate: float


class MarketDataFetcher:
    """
    Aggregates and provides market data for German real estate analysis.

    Combines data from multiple sources and provides city-level analytics.
    Includes synthetic but realistic data based on actual market trends.
    """

    def __init__(self):
        """Initialize market data fetcher."""
        self._city_data_cache: Dict[str, CityMarketData] = {}
        self._last_update: Optional[datetime] = None

        # Price multipliers by district quality (relative to city average)
        self._district_quality_multipliers = {
            "premium": 1.4,
            "good": 1.15,
            "average": 1.0,
            "below_average": 0.85,
            "affordable": 0.7
        }

        # Base data dynamically generated from config GERMAN_CITIES
        self._base_city_data = self._initialize_city_base_data()

    def _initialize_city_base_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize base market data for all cities from config.

        Dynamically generates market data based on city characteristics
        from the GERMAN_CITIES configuration.
        """
        base_data = {}

        for city_key, city_info in GERMAN_CITIES.items():
            # Generate realistic market data based on city characteristics
            avg_price = city_info.avg_price_sqm
            avg_rent = city_info.avg_rent_sqm
            population = city_info.population

            # Price range based on average (typically 30% below to 60% above average)
            price_range_low = avg_price * 0.65
            price_range_high = avg_price * 1.65

            # Price change correlates with price level (more expensive = bigger correction)
            if avg_price > 7000:
                price_yoy_change = random.uniform(-8.0, -5.0)
            elif avg_price > 5000:
                price_yoy_change = random.uniform(-6.0, -3.5)
            elif avg_price > 3500:
                price_yoy_change = random.uniform(-4.5, -2.0)
            else:
                price_yoy_change = random.uniform(-3.0, -0.5)

            # Rent growth (typically positive, higher in tight markets)
            if avg_rent > 14:
                rent_yoy_change = random.uniform(4.0, 6.0)
            elif avg_rent > 11:
                rent_yoy_change = random.uniform(3.5, 5.0)
            else:
                rent_yoy_change = random.uniform(3.0, 4.5)

            # Inventory months (larger cities = tighter markets)
            if population > 1000000:
                inventory_months = random.uniform(4.0, 5.5)
            elif population > 500000:
                inventory_months = random.uniform(4.5, 6.0)
            elif population > 200000:
                inventory_months = random.uniform(5.0, 7.0)
            else:
                inventory_months = random.uniform(5.5, 8.0)

            # Days on market (inverse of market activity)
            days_on_market = inventory_months * 10 + random.uniform(-5, 10)

            # Unemployment rate by region (approximation)
            state = city_info.state
            if state in ["Bayern", "Baden-Württemberg"]:
                unemployment_rate = random.uniform(3.0, 5.0)
            elif state in ["Hamburg", "Hessen"]:
                unemployment_rate = random.uniform(4.5, 7.0)
            elif state in ["Berlin", "Bremen"]:
                unemployment_rate = random.uniform(7.5, 10.0)
            elif state in ["Sachsen", "Thüringen", "Sachsen-Anhalt", "Brandenburg", "Mecklenburg-Vorpommern"]:
                unemployment_rate = random.uniform(5.5, 8.0)
            else:
                unemployment_rate = random.uniform(5.0, 8.0)

            # Median income correlates with price level
            median_income = max(32000, min(65000, avg_price * 6.5))

            base_data[city_key] = {
                "avg_price_sqm": avg_price,
                "price_range": (int(price_range_low), int(price_range_high)),
                "avg_rent_sqm": avg_rent,
                "price_yoy_change": round(price_yoy_change, 1),
                "rent_yoy_change": round(rent_yoy_change, 1),
                "inventory_months": round(inventory_months, 1),
                "days_on_market": int(days_on_market),
                "unemployment_rate": round(unemployment_rate, 1),
                "median_income": int(median_income),
            }

        return base_data

    def get_city_market_data(
        self,
        city_key: str,
        use_cache: bool = True
    ) -> Optional[CityMarketData]:
        """
        Get comprehensive market data for a city.

        Args:
            city_key: City identifier (e.g., "muenchen", "berlin")
            use_cache: Whether to use cached data

        Returns:
            CityMarketData object or None if city not found
        """
        if city_key not in self._base_city_data:
            logger.warning(f"City not found: {city_key}")
            return None

        cache_key = city_key
        if use_cache and cache_key in self._city_data_cache:
            cached = self._city_data_cache[cache_key]
            if datetime.now() - cached.date < timedelta(hours=24):
                return cached

        base = self._base_city_data[city_key]
        city_info = GERMAN_CITIES.get(city_key)

        if not city_info:
            return None

        # Calculate derived metrics
        annual_rent = base["avg_rent_sqm"] * 12
        gross_yield = annual_rent / base["avg_price_sqm"]
        price_to_rent = base["avg_price_sqm"] / annual_rent

        # Estimate median home price (80 sqm apartment)
        median_home_price = base["avg_price_sqm"] * 80
        price_to_income = median_home_price / base["median_income"]

        market_data = CityMarketData(
            city_name=city_info.name,
            city_key=city_key,
            date=datetime.now(),
            avg_price_sqm=base["avg_price_sqm"],
            price_range_low=base["price_range"][0],
            price_range_high=base["price_range"][1],
            price_yoy_change=base["price_yoy_change"],
            avg_rent_sqm=base["avg_rent_sqm"],
            rent_yoy_change=base["rent_yoy_change"],
            gross_rental_yield=gross_yield,
            price_to_rent_ratio=price_to_rent,
            inventory_months=base["inventory_months"],
            days_on_market=base["days_on_market"],
            price_to_income=price_to_income,
            population=city_info.population,
            unemployment_rate=base["unemployment_rate"]
        )

        self._city_data_cache[cache_key] = market_data
        return market_data

    def get_all_cities_data(self) -> Dict[str, CityMarketData]:
        """Get market data for all tracked cities."""
        result = {}
        for city_key in self._base_city_data.keys():
            data = self.get_city_market_data(city_key)
            if data:
                result[city_key] = data
        return result

    def get_price_by_plz(
        self,
        plz: str,
        property_type: str = "Wohnung",
        sqm: float = 80
    ) -> Dict[str, Any]:
        """
        Estimate property price based on postal code.

        Args:
            plz: German postal code (5 digits)
            property_type: "Wohnung" or "Haus"
            sqm: Property size in square meters

        Returns:
            Dictionary with price estimates and market data
        """
        city_key = PLZ_CITY_MAPPING.get(plz, "")

        if not city_key:
            # Return average German prices for unknown PLZ
            return {
                "plz": plz,
                "city": "Unbekannt",
                "avg_price_sqm": 3500,
                "estimated_price": 3500 * sqm,
                "confidence": "low",
                "note": "PLZ nicht in Datenbank"
            }

        city_data = self.get_city_market_data(city_key)
        if not city_data:
            return {
                "plz": plz,
                "city": "Unbekannt",
                "avg_price_sqm": 3500,
                "estimated_price": 3500 * sqm,
                "confidence": "low",
            }

        # Adjust for property type
        type_multiplier = 1.0 if property_type == "Wohnung" else 1.15

        # Estimate price
        base_price = city_data.avg_price_sqm * type_multiplier

        # Add some variation based on PLZ (simulating district quality)
        plz_hash = sum(int(d) for d in plz) % 10
        district_factor = 0.85 + (plz_hash / 10) * 0.3  # Range 0.85-1.15

        final_price_sqm = base_price * district_factor

        return {
            "plz": plz,
            "city": city_data.city_name,
            "city_key": city_key,
            "avg_price_sqm": round(final_price_sqm, 2),
            "city_avg_price_sqm": city_data.avg_price_sqm,
            "estimated_price": round(final_price_sqm * sqm, 2),
            "price_range_low": round(city_data.price_range_low * district_factor * sqm, 2),
            "price_range_high": round(city_data.price_range_high * district_factor * sqm, 2),
            "rental_yield": city_data.gross_rental_yield,
            "price_to_rent": city_data.price_to_rent_ratio,
            "confidence": "medium",
        }

    def get_rental_estimate(
        self,
        plz: str,
        sqm: float,
        property_type: str = "Wohnung",
        condition: str = "normal"
    ) -> Dict[str, Any]:
        """
        Estimate monthly rent for a property.

        Args:
            plz: Postal code
            sqm: Property size
            property_type: Property type
            condition: "premium", "good", "normal", "renovierungsbedürftig"

        Returns:
            Dictionary with rental estimates
        """
        city_key = PLZ_CITY_MAPPING.get(plz, "")

        # Condition multipliers
        condition_factors = {
            "premium": 1.25,
            "good": 1.10,
            "normal": 1.0,
            "renovierungsbedürftig": 0.80
        }
        condition_factor = condition_factors.get(condition, 1.0)

        if city_key:
            city_data = self.get_city_market_data(city_key)
            if city_data:
                base_rent = city_data.avg_rent_sqm * sqm * condition_factor
                return {
                    "plz": plz,
                    "city": city_data.city_name,
                    "monthly_rent": round(base_rent, 2),
                    "annual_rent": round(base_rent * 12, 2),
                    "rent_per_sqm": round(city_data.avg_rent_sqm * condition_factor, 2),
                    "city_avg_rent_sqm": city_data.avg_rent_sqm,
                    "confidence": "medium"
                }

        # Fallback for unknown PLZ
        avg_rent_sqm = 11.0  # German average
        base_rent = avg_rent_sqm * sqm * condition_factor
        return {
            "plz": plz,
            "city": "Unbekannt",
            "monthly_rent": round(base_rent, 2),
            "annual_rent": round(base_rent * 12, 2),
            "rent_per_sqm": round(avg_rent_sqm * condition_factor, 2),
            "confidence": "low"
        }

    def get_market_comparison(self, cities: List[str]) -> pd.DataFrame:
        """
        Compare market metrics across multiple cities.

        Args:
            cities: List of city keys

        Returns:
            DataFrame with comparison metrics
        """
        data = []
        for city_key in cities:
            city_data = self.get_city_market_data(city_key)
            if city_data:
                data.append({
                    "Stadt": city_data.city_name,
                    "Preis/qm": city_data.avg_price_sqm,
                    "Miete/qm": city_data.avg_rent_sqm,
                    "Rendite": f"{city_data.gross_rental_yield:.1%}",
                    "P/R Ratio": f"{city_data.price_to_rent_ratio:.1f}x",
                    "P/I Ratio": f"{city_data.price_to_income:.1f}x",
                    "YoY Preis": f"{city_data.price_yoy_change:+.1f}%",
                    "Inventory": f"{city_data.inventory_months:.1f} Mon.",
                    "Arbeitslosigkeit": f"{city_data.unemployment_rate:.1f}%",
                })

        return pd.DataFrame(data)

    def get_historical_prices(
        self,
        city_key: str,
        years: int = 10
    ) -> pd.DataFrame:
        """
        Get historical price data for a city.

        Args:
            city_key: City identifier
            years: Number of years of history

        Returns:
            DataFrame with historical prices
        """
        if city_key not in self._base_city_data:
            return pd.DataFrame()

        current_price = self._base_city_data[city_key]["avg_price_sqm"]

        # Generate historical data based on German market trends
        # Peak was around Q1 2022, then correction started
        dates = pd.date_range(
            end=datetime.now(),
            periods=years * 12,
            freq="M"
        )

        prices = []
        for date in dates:
            year = date.year
            month = date.month

            # Calculate historical price based on trend
            # Growth from 2015-2021, peak in 2022, decline 2023-2024
            if year <= 2015:
                factor = 0.55
            elif year <= 2019:
                factor = 0.55 + (year - 2015) * 0.10
            elif year == 2020:
                factor = 0.95 + month * 0.005
            elif year == 2021:
                factor = 1.01 + month * 0.012
            elif year == 2022:
                if month <= 3:
                    factor = 1.15 + month * 0.02
                else:
                    factor = 1.21 - (month - 3) * 0.015
            elif year == 2023:
                factor = 1.06 - month * 0.008
            else:  # 2024
                factor = 0.98 - month * 0.002

            price = current_price / factor if factor > 0 else current_price
            prices.append(price)

        # Adjust to end at current price
        prices = [p * (current_price / prices[-1]) for p in prices]

        return pd.DataFrame({
            "date": dates,
            "price_sqm": prices
        }).set_index("date")

    def get_market_health_score(self, city_key: str) -> Dict[str, Any]:
        """
        Calculate market health score for a city.

        Returns a score 0-100 where higher is healthier (less crash risk).

        Args:
            city_key: City identifier

        Returns:
            Dictionary with scores and analysis
        """
        city_data = self.get_city_market_data(city_key)
        if not city_data:
            return {"score": 50, "status": "unknown"}

        scores = {}

        # Price-to-Rent Score (lower is better, 20-25 is healthy)
        pr_ratio = city_data.price_to_rent_ratio
        if pr_ratio <= 22:
            scores["price_to_rent"] = 100
        elif pr_ratio <= 25:
            scores["price_to_rent"] = 80
        elif pr_ratio <= 30:
            scores["price_to_rent"] = 50
        elif pr_ratio <= 35:
            scores["price_to_rent"] = 25
        else:
            scores["price_to_rent"] = 0

        # Price-to-Income Score (lower is better, 5-6 is healthy)
        pi_ratio = city_data.price_to_income
        if pi_ratio <= 5.5:
            scores["price_to_income"] = 100
        elif pi_ratio <= 6.5:
            scores["price_to_income"] = 75
        elif pi_ratio <= 7.5:
            scores["price_to_income"] = 50
        elif pi_ratio <= 9:
            scores["price_to_income"] = 25
        else:
            scores["price_to_income"] = 0

        # Inventory Score (4-6 months is healthy)
        inv = city_data.inventory_months
        if 4 <= inv <= 6:
            scores["inventory"] = 100
        elif 3 <= inv < 4 or 6 < inv <= 7:
            scores["inventory"] = 70
        elif inv < 3:
            scores["inventory"] = 40  # Shortage
        else:
            scores["inventory"] = 30  # Oversupply

        # Rental Yield Score (higher is better)
        yield_pct = city_data.gross_rental_yield * 100
        if yield_pct >= 5:
            scores["rental_yield"] = 100
        elif yield_pct >= 4:
            scores["rental_yield"] = 80
        elif yield_pct >= 3:
            scores["rental_yield"] = 50
        else:
            scores["rental_yield"] = 25

        # Employment Score
        unemp = city_data.unemployment_rate
        if unemp <= 4:
            scores["unemployment"] = 100
        elif unemp <= 6:
            scores["unemployment"] = 75
        elif unemp <= 8:
            scores["unemployment"] = 50
        else:
            scores["unemployment"] = 25

        # Calculate weighted average
        weights = {
            "price_to_rent": 0.25,
            "price_to_income": 0.25,
            "inventory": 0.20,
            "rental_yield": 0.15,
            "unemployment": 0.15
        }

        total_score = sum(scores[k] * weights[k] for k in scores)

        # Determine status
        if total_score >= 70:
            status = "healthy"
        elif total_score >= 50:
            status = "moderate"
        elif total_score >= 30:
            status = "caution"
        else:
            status = "high_risk"

        return {
            "score": round(total_score, 1),
            "status": status,
            "component_scores": scores,
            "city": city_data.city_name,
        }


# Singleton instance
market_data_fetcher = MarketDataFetcher()
