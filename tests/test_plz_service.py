"""
Tests for the German PLZ (Postal Code) Service.

Tests coverage:
- Bundesland lookup for all PLZ prefixes
- City market data retrieval
- Price interpolation based on distance
- Edge cases and error handling
"""

import pytest
import math

from src.utils.plz_service import (
    PLZService, plz_service,
    MAJOR_CITIES, PLZ_PREFIX_TO_BUNDESLAND,
    haversine_distance, CityMarketData
)


class TestPLZPrefixMapping:
    """Tests for PLZ prefix to Bundesland mapping."""

    def test_all_bundeslaender_covered(self):
        """Verify all 16 Bundesländer are represented in mapping."""
        bundeslaender = set(PLZ_PREFIX_TO_BUNDESLAND.values())
        expected = {
            "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg",
            "Bremen", "Hamburg", "Hessen", "Mecklenburg-Vorpommern",
            "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz",
            "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein",
            "Thüringen"
        }
        assert bundeslaender == expected

    def test_major_city_plz_prefixes(self):
        """Verify major cities have correct Bundesland assignments."""
        test_cases = [
            ("10", "Berlin"),      # Berlin
            ("20", "Hamburg"),     # Hamburg
            ("80", "Bayern"),      # München
            ("50", "Nordrhein-Westfalen"),  # Köln
            ("60", "Hessen"),      # Frankfurt
            ("70", "Baden-Württemberg"),    # Stuttgart
        ]
        for prefix, expected_land in test_cases:
            assert PLZ_PREFIX_TO_BUNDESLAND.get(prefix) == expected_land

    def test_plz_prefix_format(self):
        """Verify all prefixes are 2-digit strings."""
        for prefix in PLZ_PREFIX_TO_BUNDESLAND.keys():
            assert len(prefix) == 2
            assert prefix.isdigit()


class TestPLZServiceBundesland:
    """Tests for Bundesland lookup functionality."""

    def test_get_bundesland_valid_plz(self):
        """Test Bundesland lookup with valid PLZ."""
        service = PLZService()
        assert service.get_bundesland("80331") == "Bayern"
        assert service.get_bundesland("10115") == "Berlin"
        assert service.get_bundesland("50667") == "Nordrhein-Westfalen"

    def test_get_bundesland_edge_cases(self):
        """Test Bundesland lookup edge cases."""
        service = PLZService()
        # Empty or too short
        assert service.get_bundesland("") is None
        assert service.get_bundesland("1") is None
        # Unknown prefix (05 doesn't exist in Germany)
        assert service.get_bundesland("05123") is None

    def test_get_bundesland_all_prefixes(self):
        """Verify all mapped prefixes return valid Bundesland."""
        service = PLZService()
        for prefix in PLZ_PREFIX_TO_BUNDESLAND.keys():
            result = service.get_bundesland(prefix + "000")
            assert result is not None
            assert isinstance(result, str)


class TestMajorCities:
    """Tests for major cities database."""

    def test_top_7_cities_present(self):
        """Verify all top 7 German cities (A-cities) are present."""
        top_7 = ["Berlin", "Hamburg", "München", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf"]
        for city in top_7:
            assert city in MAJOR_CITIES

    def test_city_data_completeness(self):
        """Verify all city data has required fields."""
        for city_name, data in MAJOR_CITIES.items():
            assert isinstance(data, CityMarketData)
            assert data.name
            assert data.bundesland
            assert data.plz_prefix
            assert data.avg_price_sqm > 0
            assert data.avg_rent_sqm > 0
            assert -90 <= data.latitude <= 90
            assert -180 <= data.longitude <= 180

    def test_city_prices_realistic(self):
        """Verify city prices are within realistic German ranges."""
        for city_name, data in MAJOR_CITIES.items():
            # German prices typically between 1,500 and 12,000 EUR/sqm
            assert 1500 <= data.avg_price_sqm <= 12000, f"{city_name} price out of range"
            # German rents typically between 6 and 25 EUR/sqm
            assert 6 <= data.avg_rent_sqm <= 25, f"{city_name} rent out of range"


class TestHaversineDistance:
    """Tests for distance calculation."""

    def test_same_point(self):
        """Distance to same point should be 0."""
        dist = haversine_distance(52.52, 13.405, 52.52, 13.405)
        assert dist == 0.0

    def test_known_distances(self):
        """Test known distances between German cities."""
        # Berlin to München is approximately 500 km
        dist = haversine_distance(52.52, 13.405, 48.137, 11.576)
        assert 480 < dist < 520

        # Hamburg to Köln is approximately 360 km
        dist = haversine_distance(53.551, 9.993, 50.937, 6.960)
        assert 340 < dist < 380

    def test_symmetry(self):
        """Distance should be symmetric."""
        d1 = haversine_distance(52.52, 13.405, 48.137, 11.576)
        d2 = haversine_distance(48.137, 11.576, 52.52, 13.405)
        assert abs(d1 - d2) < 0.01


class TestPLZServiceInterpolation:
    """Tests for market data interpolation."""

    def test_interpolate_major_city_plz(self):
        """Interpolation for major city PLZ should return city data."""
        service = PLZService()
        # München center
        result = service.interpolate_market_data("80331")
        assert result is not None
        assert result["city"] == "München"
        assert result["bundesland"] == "Bayern"

    def test_interpolate_applies_distance_discount(self):
        """Prices should decrease with distance from city center."""
        service = PLZService()
        # Get city center data
        center = service.interpolate_market_data("80331")
        # Get suburban data (different PLZ prefix but same region)
        suburban = service.interpolate_market_data("85123")

        # Suburban should have lower prices (distance discount)
        if center and suburban:
            assert suburban["adjustment_factor"] <= 1.0

    def test_interpolate_unknown_plz(self):
        """Interpolation for unknown PLZ should return None or best match."""
        service = PLZService()
        # 05xxx doesn't exist in Germany
        result = service.interpolate_market_data("05123")
        # Should return None since prefix not in coordinates
        assert result is None

    def test_interpolate_returns_distance(self):
        """Interpolation should include distance to nearest city."""
        service = PLZService()
        result = service.interpolate_market_data("80331")
        assert result is not None
        assert "distance_km" in result
        assert result["distance_km"] >= 0


class TestPLZServiceUtilities:
    """Tests for utility methods."""

    def test_list_all_cities(self):
        """Test city listing returns sorted list."""
        service = PLZService()
        cities = service.list_all_cities()
        assert len(cities) >= 50  # At least 50 cities
        assert cities == sorted(cities)  # Sorted

    def test_get_cities_by_bundesland(self):
        """Test filtering cities by Bundesland."""
        service = PLZService()

        bayern_cities = service.get_cities_by_bundesland("Bayern")
        assert len(bayern_cities) >= 3  # München, Nürnberg, Augsburg at least
        for city in bayern_cities:
            assert city.bundesland == "Bayern"

    def test_get_city_data(self):
        """Test direct city data retrieval."""
        service = PLZService()

        berlin = service.get_city_data("Berlin")
        assert berlin is not None
        assert berlin.bundesland == "Berlin"

        unknown = service.get_city_data("Fantasiestadt")
        assert unknown is None


class TestPLZServiceNearestCity:
    """Tests for nearest city lookup."""

    def test_nearest_city_berlin(self):
        """PLZ in Berlin should have Berlin as nearest city."""
        service = PLZService()
        nearest, distance = service.get_nearest_city("10115")
        assert nearest is not None
        assert nearest.name == "Berlin"
        assert distance < 50  # Within 50km

    def test_nearest_city_invalid_plz(self):
        """Invalid PLZ should return None."""
        service = PLZService()
        nearest, distance = service.get_nearest_city("")
        assert nearest is None
        assert distance == float('inf')


# Run with: pytest tests/test_plz_service.py -v
