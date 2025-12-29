"""
Bundesbank Data Fetcher for German Real Estate Investment Analysis System.

Fetches data from Deutsche Bundesbank's public API including:
- Interest rates (mortgage rates, Bund yields)
- Credit volumes to households
- Household debt statistics

API Documentation: https://www.bundesbank.de/de/statistiken/zeitreihen-datenbanken
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BundesbankSeries:
    """Definition of a Bundesbank time series."""
    series_key: str
    name: str
    description: str
    unit: str
    frequency: str  # D=daily, M=monthly, Q=quarterly, A=annual


# Key series for real estate analysis
BUNDESBANK_SERIES = {
    # Interest rates
    "mortgage_rate": BundesbankSeries(
        series_key="BBK01.SU0112",
        name="Mortgage Rate (New Business)",
        description="Interest rates on new housing loans to households, pure new business",
        unit="Percent",
        frequency="M"
    ),
    "mortgage_rate_10y": BundesbankSeries(
        series_key="BBK01.SU0509",
        name="Housing Loan Rate 10Y Fixed",
        description="Interest rates housing loans 10Y+ initial rate fixation",
        unit="Percent",
        frequency="M"
    ),
    "bund_10y": BundesbankSeries(
        series_key="BBK01.WU3141",
        name="10Y Bund Yield",
        description="Government bond yield 10-year residual maturity",
        unit="Percent",
        frequency="D"
    ),
    "bund_2y": BundesbankSeries(
        series_key="BBK01.WU0004",
        name="2Y Bund Yield",
        description="Government bond yield 2-year residual maturity",
        unit="Percent",
        frequency="D"
    ),
    # Credit data
    "housing_loans_outstanding": BundesbankSeries(
        series_key="BBK01.PQ3011",
        name="Housing Loans Outstanding",
        description="Outstanding loans to households for house purchase",
        unit="Mio EUR",
        frequency="M"
    ),
    "housing_loans_new": BundesbankSeries(
        series_key="BBK01.SU0101",
        name="New Housing Loans",
        description="New loans to households for house purchase",
        unit="Mio EUR",
        frequency="M"
    ),
    # Monetary aggregates
    "m3_money_supply": BundesbankSeries(
        series_key="BBK01.TTA100",
        name="M3 Money Supply",
        description="M3 monetary aggregate",
        unit="Mio EUR",
        frequency="M"
    ),
}


class BundesbankFetcher:
    """
    Fetches data from the Deutsche Bundesbank statistical database.

    Uses the Bundesbank's SDMX REST API for structured data access.
    """

    BASE_URL = "https://api.statistiken.bundesbank.de/rest/data"

    def __init__(self, cache_hours: int = 24):
        """
        Initialize the Bundesbank data fetcher.

        Args:
            cache_hours: Hours to cache API responses
        """
        self.cache_hours = cache_hours
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "GermanRealEstateAnalyzer/1.0"
        })

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache:
            return False
        cached_time, _ = self._cache[cache_key]
        return datetime.now() - cached_time < timedelta(hours=self.cache_hours)

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid."""
        if self._is_cache_valid(cache_key):
            _, data = self._cache[cache_key]
            return data
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache."""
        self._cache[cache_key] = (datetime.now(), data)

    def fetch_series(
        self,
        series_key: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch a time series from Bundesbank.

        Args:
            series_key: The Bundesbank series key (e.g., "BBK01.WU3141")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            use_cache: Whether to use cached data

        Returns:
            DataFrame with date index and value column
        """
        cache_key = f"bbk_{series_key}_{start_date}_{end_date}"

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        # Parse series key
        parts = series_key.split(".")
        if len(parts) != 2:
            raise ValueError(f"Invalid series key format: {series_key}")

        flow_ref, key = parts

        # Build URL
        url = f"{self.BASE_URL}/{flow_ref}/{key}"

        params = {}
        if start_date:
            params["startPeriod"] = start_date[:7]  # YYYY-MM format
        if end_date:
            params["endPeriod"] = end_date[:7]

        try:
            logger.info(f"Fetching Bundesbank series: {series_key}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = self._parse_response(data)

            if use_cache and not df.empty:
                self._set_cache(cache_key, df)

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Bundesbank data: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame(columns=["date", "value"])

    def _parse_response(self, data: Dict) -> pd.DataFrame:
        """
        Parse Bundesbank JSON response into DataFrame.

        The Bundesbank uses SDMX-JSON format.
        """
        try:
            # Navigate SDMX-JSON structure
            datasets = data.get("data", {}).get("dataSets", [])
            if not datasets:
                return pd.DataFrame(columns=["date", "value"])

            series_data = datasets[0].get("series", {})
            if not series_data:
                return pd.DataFrame(columns=["date", "value"])

            # Get dimension values for time period
            structure = data.get("data", {}).get("structure", {})
            dimensions = structure.get("dimensions", {}).get("observation", [])

            time_periods = []
            for dim in dimensions:
                if dim.get("id") == "TIME_PERIOD":
                    time_periods = [v["id"] for v in dim.get("values", [])]
                    break

            # Extract observations
            records = []
            for series_key, series_values in series_data.items():
                observations = series_values.get("observations", {})
                for idx_str, obs_data in observations.items():
                    idx = int(idx_str)
                    if idx < len(time_periods):
                        period = time_periods[idx]
                        value = obs_data[0] if obs_data else None
                        if value is not None:
                            # Convert period to date
                            date_str = self._period_to_date(period)
                            records.append({"date": date_str, "value": float(value)})

            df = pd.DataFrame(records)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                df = df.set_index("date")

            return df

        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Failed to parse Bundesbank response: {e}")
            return pd.DataFrame(columns=["date", "value"])

    def _period_to_date(self, period: str) -> str:
        """Convert Bundesbank period string to date."""
        # Handle formats: YYYY, YYYY-MM, YYYY-QN, YYYY-MM-DD
        if len(period) == 4:  # Annual
            return f"{period}-12-31"
        elif "-Q" in period:  # Quarterly
            year, quarter = period.split("-Q")
            month = int(quarter) * 3
            return f"{year}-{month:02d}-01"
        elif len(period) == 7:  # Monthly YYYY-MM
            return f"{period}-01"
        else:
            return period

    def get_mortgage_rates(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get mortgage interest rates for new housing loans.

        Returns:
            DataFrame with mortgage rate time series
        """
        series = BUNDESBANK_SERIES["mortgage_rate"]
        return self.fetch_series(series.series_key, start_date, end_date)

    def get_mortgage_rate_10y(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Get mortgage rates with 10+ year fixed period."""
        series = BUNDESBANK_SERIES["mortgage_rate_10y"]
        return self.fetch_series(series.series_key, start_date, end_date)

    def get_bund_yield(
        self,
        maturity: str = "10y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get German government bond yields.

        Args:
            maturity: "10y" or "2y"
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with yield time series
        """
        series_key = "bund_10y" if maturity == "10y" else "bund_2y"
        series = BUNDESBANK_SERIES[series_key]
        return self.fetch_series(series.series_key, start_date, end_date)

    def get_yield_curve_spread(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculate yield curve spread (10Y - 2Y).

        Inversion (negative spread) is a recession indicator.

        Returns:
            DataFrame with yield spread time series
        """
        bund_10y = self.get_bund_yield("10y", start_date, end_date)
        bund_2y = self.get_bund_yield("2y", start_date, end_date)

        if bund_10y.empty or bund_2y.empty:
            return pd.DataFrame(columns=["value"])

        # Align dates and calculate spread
        spread = bund_10y.join(bund_2y, lsuffix="_10y", rsuffix="_2y", how="inner")
        spread["value"] = spread["value_10y"] - spread["value_2y"]
        return spread[["value"]]

    def get_housing_loan_volume(
        self,
        outstanding: bool = True,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get housing loan volumes.

        Args:
            outstanding: If True, get outstanding loans; if False, new loans
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with loan volume time series
        """
        series_key = "housing_loans_outstanding" if outstanding else "housing_loans_new"
        series = BUNDESBANK_SERIES[series_key]
        return self.fetch_series(series.series_key, start_date, end_date)

    def get_credit_growth(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Calculate year-over-year credit growth for housing loans.

        Returns:
            DataFrame with credit growth percentage
        """
        loans = self.get_housing_loan_volume(True, start_date, end_date)
        if loans.empty:
            return pd.DataFrame(columns=["value"])

        # Calculate YoY growth
        loans["value_yoy"] = loans["value"].pct_change(periods=12) * 100
        return loans[["value_yoy"]].rename(columns={"value_yoy": "value"}).dropna()

    def get_current_rates(self) -> Dict[str, float]:
        """
        Get current key interest rates.

        Returns:
            Dictionary with current rate values
        """
        rates = {}

        # Get latest mortgage rate
        mortgage = self.get_mortgage_rates()
        if not mortgage.empty:
            rates["mortgage_rate"] = mortgage["value"].iloc[-1]

        # Get latest 10Y Bund
        bund = self.get_bund_yield("10y")
        if not bund.empty:
            rates["bund_10y"] = bund["value"].iloc[-1]

        # Get yield spread
        spread = self.get_yield_curve_spread()
        if not spread.empty:
            rates["yield_spread"] = spread["value"].iloc[-1]

        return rates

    def get_all_key_indicators(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch all key indicators for real estate analysis.

        Returns:
            Dictionary mapping indicator names to DataFrames
        """
        indicators = {}

        for name, series in BUNDESBANK_SERIES.items():
            try:
                df = self.fetch_series(series.series_key, start_date, end_date)
                if not df.empty:
                    indicators[name] = df
            except Exception as e:
                logger.warning(f"Failed to fetch {name}: {e}")

        return indicators


# Singleton instance
bundesbank_fetcher = BundesbankFetcher()
