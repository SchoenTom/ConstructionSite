"""
Database Manager for German Real Estate Investment Analysis System.

Handles SQLite database operations for storing time-series data,
analysis results, and cached API responses.
"""

import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import json
import os
from pathlib import Path

from .config import config


class DatabaseManager:
    """
    Manages SQLite database operations for real estate data.

    Stores:
    - Time series data (interest rates, price indices, etc.)
    - Calculated metrics and scores
    - API response cache
    - User analysis history
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file (uses config default if None)
        """
        self.db_path = db_path or config.database_path

        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Time series data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    value REAL NOT NULL,
                    source TEXT,
                    unit TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(series_id, date)
                )
            """)

            # Create index on series_id and date
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_series_lookup
                ON time_series(series_id, date)
            """)

            # Market indicators table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_name TEXT NOT NULL,
                    city TEXT,
                    date TEXT NOT NULL,
                    value REAL NOT NULL,
                    previous_value REAL,
                    change_pct REAL,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(indicator_name, city, date)
                )
            """)

            # Crash probability scores history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crash_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    city TEXT,
                    total_score REAL NOT NULL,
                    valuation_score REAL,
                    credit_score REAL,
                    supply_demand_score REAL,
                    macro_score REAL,
                    fundamentals_score REAL,
                    recommendation TEXT,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, city)
                )
            """)

            # API cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    data TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Property analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS property_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_date TEXT NOT NULL,
                    property_type TEXT,
                    city TEXT,
                    plz TEXT,
                    purchase_price REAL,
                    sqm REAL,
                    ltv REAL,
                    interest_rate REAL,
                    term_years INTEGER,
                    npv REAL,
                    irr REAL,
                    cash_on_cash REAL,
                    recommendation TEXT,
                    full_analysis TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # City statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS city_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    city TEXT NOT NULL,
                    date TEXT NOT NULL,
                    avg_price_sqm REAL,
                    avg_rent_sqm REAL,
                    price_to_rent REAL,
                    price_to_income REAL,
                    inventory_months REAL,
                    unemployment_rate REAL,
                    population REAL,
                    source TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(city, date)
                )
            """)

    def insert_time_series(
        self,
        series_id: str,
        date_value: str,
        value: float,
        source: Optional[str] = None,
        unit: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Insert a time series data point.

        Args:
            series_id: Identifier for the series (e.g., "BBK01.WU3141")
            date_value: Date string (YYYY-MM-DD)
            value: Numeric value
            source: Data source name
            unit: Unit of measurement
            metadata: Additional metadata as dict

        Returns:
            Row ID of inserted record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO time_series
                (series_id, date, value, source, unit, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                series_id,
                date_value,
                value,
                source,
                unit,
                json.dumps(metadata) if metadata else None
            ))
            return cursor.lastrowid

    def insert_time_series_batch(
        self,
        series_id: str,
        data: List[Tuple[str, float]],
        source: Optional[str] = None,
        unit: Optional[str] = None
    ):
        """
        Insert multiple time series data points efficiently.

        Args:
            series_id: Identifier for the series
            data: List of (date, value) tuples
            source: Data source name
            unit: Unit of measurement
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO time_series
                (series_id, date, value, source, unit)
                VALUES (?, ?, ?, ?, ?)
            """, [(series_id, d, v, source, unit) for d, v in data])

    def get_time_series(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve time series data.

        Args:
            series_id: Series identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records

        Returns:
            List of dictionaries with date and value
        """
        query = "SELECT date, value FROM time_series WHERE series_id = ?"
        params: List[Any] = [series_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [{"date": row["date"], "value": row["value"]} for row in cursor.fetchall()]

    def get_latest_value(self, series_id: str) -> Optional[Dict]:
        """Get the most recent value for a series."""
        result = self.get_time_series(series_id, limit=1)
        return result[0] if result else None

    def insert_crash_score(
        self,
        date_value: str,
        total_score: float,
        city: Optional[str] = None,
        valuation_score: Optional[float] = None,
        credit_score: Optional[float] = None,
        supply_demand_score: Optional[float] = None,
        macro_score: Optional[float] = None,
        fundamentals_score: Optional[float] = None,
        recommendation: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> int:
        """Insert crash probability score."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO crash_scores
                (date, city, total_score, valuation_score, credit_score,
                 supply_demand_score, macro_score, fundamentals_score,
                 recommendation, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_value,
                city,
                total_score,
                valuation_score,
                credit_score,
                supply_demand_score,
                macro_score,
                fundamentals_score,
                recommendation,
                json.dumps(details) if details else None
            ))
            return cursor.lastrowid

    def get_crash_scores(
        self,
        city: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Retrieve crash probability scores."""
        query = "SELECT * FROM crash_scores WHERE 1=1"
        params: List[Any] = []

        if city:
            query += " AND city = ?"
            params.append(city)

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def insert_city_statistics(
        self,
        city: str,
        date_value: str,
        stats: Dict[str, float],
        source: Optional[str] = None
    ):
        """Insert city-level statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO city_statistics
                (city, date, avg_price_sqm, avg_rent_sqm, price_to_rent,
                 price_to_income, inventory_months, unemployment_rate,
                 population, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                city,
                date_value,
                stats.get("avg_price_sqm"),
                stats.get("avg_rent_sqm"),
                stats.get("price_to_rent"),
                stats.get("price_to_income"),
                stats.get("inventory_months"),
                stats.get("unemployment_rate"),
                stats.get("population"),
                source
            ))

    def get_city_statistics(
        self,
        city: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Retrieve city statistics."""
        query = "SELECT * FROM city_statistics WHERE city = ?"
        params: List[Any] = [city]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " ORDER BY date DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def cache_api_response(
        self,
        cache_key: str,
        data: Any,
        expires_hours: int = 24
    ):
        """Cache an API response."""
        expires_at = datetime.now().replace(
            hour=datetime.now().hour + expires_hours
        ).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO api_cache
                (cache_key, data, expires_at)
                VALUES (?, ?, ?)
            """, (cache_key, json.dumps(data), expires_at))

    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached API response if not expired."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT data FROM api_cache
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return None

    def clear_expired_cache(self):
        """Remove expired cache entries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM api_cache WHERE expires_at < ?
            """, (datetime.now().isoformat(),))

    def insert_property_analysis(
        self,
        analysis_data: Dict[str, Any]
    ) -> int:
        """Store a property investment analysis."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO property_analyses
                (analysis_date, property_type, city, plz, purchase_price,
                 sqm, ltv, interest_rate, term_years, npv, irr,
                 cash_on_cash, recommendation, full_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().date().isoformat(),
                analysis_data.get("property_type"),
                analysis_data.get("city"),
                analysis_data.get("plz"),
                analysis_data.get("purchase_price"),
                analysis_data.get("sqm"),
                analysis_data.get("ltv"),
                analysis_data.get("interest_rate"),
                analysis_data.get("term_years"),
                analysis_data.get("npv"),
                analysis_data.get("irr"),
                analysis_data.get("cash_on_cash"),
                analysis_data.get("recommendation"),
                json.dumps(analysis_data)
            ))
            return cursor.lastrowid

    def get_database_stats(self) -> Dict[str, int]:
        """Get statistics about database contents."""
        stats = {}
        tables = [
            "time_series", "market_indicators", "crash_scores",
            "api_cache", "property_analyses", "city_statistics"
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()["count"]

        return stats


# Global database manager instance
db = DatabaseManager()
