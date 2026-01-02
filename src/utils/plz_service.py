"""
German PLZ (Postal Code) Service.

Provides complete coverage of all German postal codes with:
- Bundesland determination from PLZ prefix
- City market data for 55+ major cities
- Price interpolation for any PLZ based on nearest major city
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import math


# Complete mapping of PLZ prefixes (Leitregionen) to Bundesländer
PLZ_PREFIX_TO_BUNDESLAND: Dict[str, str] = {
    # 0x - Sachsen, Sachsen-Anhalt, Thüringen
    "01": "Sachsen", "02": "Sachsen", "03": "Brandenburg", "04": "Sachsen",
    "06": "Sachsen-Anhalt", "07": "Thüringen", "08": "Sachsen", "09": "Sachsen",
    # 1x - Berlin, Brandenburg
    "10": "Berlin", "11": "Berlin", "12": "Berlin", "13": "Berlin", "14": "Brandenburg",
    "15": "Brandenburg", "16": "Brandenburg", "17": "Mecklenburg-Vorpommern",
    "18": "Mecklenburg-Vorpommern", "19": "Mecklenburg-Vorpommern",
    # 2x - Hamburg, Schleswig-Holstein, Niedersachsen, Bremen, Mecklenburg-Vorpommern
    "20": "Hamburg", "21": "Niedersachsen", "22": "Hamburg", "23": "Schleswig-Holstein",
    "24": "Schleswig-Holstein", "25": "Schleswig-Holstein", "26": "Niedersachsen",
    "27": "Niedersachsen", "28": "Bremen", "29": "Niedersachsen",
    # 3x - Niedersachsen, Nordrhein-Westfalen
    "30": "Niedersachsen", "31": "Niedersachsen", "32": "Nordrhein-Westfalen",
    "33": "Nordrhein-Westfalen", "34": "Hessen", "35": "Hessen",
    "36": "Hessen", "37": "Niedersachsen", "38": "Niedersachsen", "39": "Sachsen-Anhalt",
    # 4x - Nordrhein-Westfalen
    "40": "Nordrhein-Westfalen", "41": "Nordrhein-Westfalen", "42": "Nordrhein-Westfalen",
    "44": "Nordrhein-Westfalen", "45": "Nordrhein-Westfalen", "46": "Nordrhein-Westfalen",
    "47": "Nordrhein-Westfalen", "48": "Nordrhein-Westfalen", "49": "Niedersachsen",
    # 5x - Nordrhein-Westfalen, Rheinland-Pfalz
    "50": "Nordrhein-Westfalen", "51": "Nordrhein-Westfalen", "52": "Nordrhein-Westfalen",
    "53": "Nordrhein-Westfalen", "54": "Rheinland-Pfalz", "55": "Rheinland-Pfalz",
    "56": "Rheinland-Pfalz", "57": "Nordrhein-Westfalen", "58": "Nordrhein-Westfalen",
    "59": "Nordrhein-Westfalen",
    # 6x - Hessen, Rheinland-Pfalz, Saarland, Baden-Württemberg
    "60": "Hessen", "61": "Hessen", "63": "Hessen", "64": "Hessen",
    "65": "Hessen", "66": "Saarland", "67": "Rheinland-Pfalz",
    "68": "Baden-Württemberg", "69": "Baden-Württemberg",
    # 7x - Baden-Württemberg
    "70": "Baden-Württemberg", "71": "Baden-Württemberg", "72": "Baden-Württemberg",
    "73": "Baden-Württemberg", "74": "Baden-Württemberg", "75": "Baden-Württemberg",
    "76": "Baden-Württemberg", "77": "Baden-Württemberg", "78": "Baden-Württemberg",
    "79": "Baden-Württemberg",
    # 8x - Bayern, Baden-Württemberg
    "80": "Bayern", "81": "Bayern", "82": "Bayern", "83": "Bayern",
    "84": "Bayern", "85": "Bayern", "86": "Bayern", "87": "Bayern",
    "88": "Baden-Württemberg", "89": "Baden-Württemberg",
    # 9x - Bayern, Thüringen, Sachsen
    "90": "Bayern", "91": "Bayern", "92": "Bayern", "93": "Bayern",
    "94": "Bayern", "95": "Bayern", "96": "Bayern", "97": "Bayern",
    "98": "Thüringen", "99": "Thüringen",
}


@dataclass
class CityMarketData:
    """Market data for a German city."""
    name: str
    bundesland: str
    plz_prefix: str  # Main PLZ prefix for the city
    avg_price_sqm: float  # Average purchase price per sqm
    avg_rent_sqm: float  # Average cold rent per sqm
    latitude: float
    longitude: float


# Major German cities with verified market data (2024/2025 estimates)
MAJOR_CITIES: Dict[str, CityMarketData] = {
    # Top 7 (A-cities)
    "Berlin": CityMarketData("Berlin", "Berlin", "10", 5200, 14.50, 52.52, 13.405),
    "Hamburg": CityMarketData("Hamburg", "Hamburg", "20", 5800, 15.20, 53.551, 9.993),
    "München": CityMarketData("München", "Bayern", "80", 9500, 21.50, 48.137, 11.576),
    "Köln": CityMarketData("Köln", "Nordrhein-Westfalen", "50", 4200, 13.80, 50.937, 6.960),
    "Frankfurt": CityMarketData("Frankfurt am Main", "Hessen", "60", 5500, 16.00, 50.110, 8.682),
    "Stuttgart": CityMarketData("Stuttgart", "Baden-Württemberg", "70", 5200, 15.50, 48.776, 9.182),
    "Düsseldorf": CityMarketData("Düsseldorf", "Nordrhein-Westfalen", "40", 4500, 14.20, 51.225, 6.776),

    # B-cities
    "Hannover": CityMarketData("Hannover", "Niedersachsen", "30", 3200, 11.50, 52.375, 9.732),
    "Leipzig": CityMarketData("Leipzig", "Sachsen", "04", 2800, 9.50, 51.340, 12.374),
    "Dresden": CityMarketData("Dresden", "Sachsen", "01", 2900, 9.80, 51.051, 13.738),
    "Nürnberg": CityMarketData("Nürnberg", "Bayern", "90", 3800, 12.50, 49.452, 11.077),
    "Bremen": CityMarketData("Bremen", "Bremen", "28", 2600, 10.20, 53.079, 8.801),
    "Dortmund": CityMarketData("Dortmund", "Nordrhein-Westfalen", "44", 2400, 9.50, 51.514, 7.468),
    "Essen": CityMarketData("Essen", "Nordrhein-Westfalen", "45", 2300, 9.20, 51.457, 7.012),
    "Duisburg": CityMarketData("Duisburg", "Nordrhein-Westfalen", "47", 1800, 7.80, 51.435, 6.762),

    # C-cities and regional centers
    "Bochum": CityMarketData("Bochum", "Nordrhein-Westfalen", "44", 2100, 8.80, 51.481, 7.216),
    "Wuppertal": CityMarketData("Wuppertal", "Nordrhein-Westfalen", "42", 1900, 8.50, 51.256, 7.150),
    "Bielefeld": CityMarketData("Bielefeld", "Nordrhein-Westfalen", "33", 2500, 9.80, 52.020, 8.532),
    "Bonn": CityMarketData("Bonn", "Nordrhein-Westfalen", "53", 3800, 13.00, 50.737, 7.099),
    "Münster": CityMarketData("Münster", "Nordrhein-Westfalen", "48", 4200, 13.50, 51.961, 7.626),
    "Karlsruhe": CityMarketData("Karlsruhe", "Baden-Württemberg", "76", 3600, 12.80, 49.009, 8.404),
    "Mannheim": CityMarketData("Mannheim", "Baden-Württemberg", "68", 3400, 12.20, 49.488, 8.467),
    "Augsburg": CityMarketData("Augsburg", "Bayern", "86", 4200, 13.80, 48.371, 10.898),
    "Wiesbaden": CityMarketData("Wiesbaden", "Hessen", "65", 4500, 14.50, 50.083, 8.240),
    "Mainz": CityMarketData("Mainz", "Rheinland-Pfalz", "55", 4000, 13.50, 50.000, 8.271),
    "Gelsenkirchen": CityMarketData("Gelsenkirchen", "Nordrhein-Westfalen", "45", 1600, 7.20, 51.518, 7.086),
    "Mönchengladbach": CityMarketData("Mönchengladbach", "Nordrhein-Westfalen", "41", 2200, 9.00, 51.185, 6.442),
    "Braunschweig": CityMarketData("Braunschweig", "Niedersachsen", "38", 2800, 10.50, 52.264, 10.526),
    "Chemnitz": CityMarketData("Chemnitz", "Sachsen", "09", 1600, 6.50, 50.833, 12.917),
    "Kiel": CityMarketData("Kiel", "Schleswig-Holstein", "24", 3000, 11.00, 54.323, 10.123),
    "Aachen": CityMarketData("Aachen", "Nordrhein-Westfalen", "52", 3200, 11.80, 50.775, 6.084),
    "Halle": CityMarketData("Halle (Saale)", "Sachsen-Anhalt", "06", 1800, 7.50, 51.482, 11.970),
    "Magdeburg": CityMarketData("Magdeburg", "Sachsen-Anhalt", "39", 1900, 7.80, 52.121, 11.628),
    "Freiburg": CityMarketData("Freiburg im Breisgau", "Baden-Württemberg", "79", 5000, 15.00, 47.999, 7.842),
    "Krefeld": CityMarketData("Krefeld", "Nordrhein-Westfalen", "47", 2100, 8.80, 51.333, 6.562),
    "Lübeck": CityMarketData("Lübeck", "Schleswig-Holstein", "23", 3200, 11.50, 53.867, 10.687),
    "Oberhausen": CityMarketData("Oberhausen", "Nordrhein-Westfalen", "46", 1700, 7.50, 51.496, 6.863),
    "Erfurt": CityMarketData("Erfurt", "Thüringen", "99", 2400, 9.00, 50.985, 11.029),
    "Rostock": CityMarketData("Rostock", "Mecklenburg-Vorpommern", "18", 2800, 10.00, 54.092, 12.099),
    "Kassel": CityMarketData("Kassel", "Hessen", "34", 2400, 9.50, 51.313, 9.480),
    "Hagen": CityMarketData("Hagen", "Nordrhein-Westfalen", "58", 1600, 7.20, 51.361, 7.474),
    "Saarbrücken": CityMarketData("Saarbrücken", "Saarland", "66", 2200, 9.00, 49.240, 6.997),
    "Potsdam": CityMarketData("Potsdam", "Brandenburg", "14", 4500, 13.50, 52.396, 13.058),
    "Hamm": CityMarketData("Hamm", "Nordrhein-Westfalen", "59", 1900, 8.00, 51.678, 7.816),
    "Ludwigshafen": CityMarketData("Ludwigshafen", "Rheinland-Pfalz", "67", 2600, 10.50, 49.477, 8.445),
    "Oldenburg": CityMarketData("Oldenburg", "Niedersachsen", "26", 2800, 10.50, 53.143, 8.214),
    "Osnabrück": CityMarketData("Osnabrück", "Niedersachsen", "49", 2700, 10.20, 52.279, 8.047),
    "Leverkusen": CityMarketData("Leverkusen", "Nordrhein-Westfalen", "51", 2800, 10.50, 51.049, 6.988),
    "Heidelberg": CityMarketData("Heidelberg", "Baden-Württemberg", "69", 4800, 14.50, 49.398, 8.672),
    "Darmstadt": CityMarketData("Darmstadt", "Hessen", "64", 4200, 14.00, 49.872, 8.651),
    "Regensburg": CityMarketData("Regensburg", "Bayern", "93", 4500, 14.00, 49.013, 12.102),
    "Würzburg": CityMarketData("Würzburg", "Bayern", "97", 3800, 12.50, 49.794, 9.929),
    "Wolfsburg": CityMarketData("Wolfsburg", "Niedersachsen", "38", 2600, 10.00, 52.423, 10.787),
    "Ingolstadt": CityMarketData("Ingolstadt", "Bayern", "85", 4800, 14.50, 48.764, 11.425),
    "Ulm": CityMarketData("Ulm", "Baden-Württemberg", "89", 4000, 13.00, 48.401, 9.988),
    "Göttingen": CityMarketData("Göttingen", "Niedersachsen", "37", 2800, 10.50, 51.541, 9.916),
    "Konstanz": CityMarketData("Konstanz", "Baden-Württemberg", "78", 5500, 16.00, 47.663, 9.175),
    "Trier": CityMarketData("Trier", "Rheinland-Pfalz", "54", 2800, 10.50, 49.757, 6.641),
    "Jena": CityMarketData("Jena", "Thüringen", "07", 2600, 9.50, 50.928, 11.586),
}


# PLZ prefix coordinates (approximate center of each region)
PLZ_PREFIX_COORDINATES: Dict[str, Tuple[float, float]] = {
    "01": (51.05, 13.74), "02": (51.18, 14.43), "03": (51.76, 14.33), "04": (51.34, 12.37),
    "06": (51.48, 11.97), "07": (50.93, 11.59), "08": (50.72, 12.49), "09": (50.83, 12.92),
    "10": (52.52, 13.38), "11": (52.52, 13.38), "12": (52.48, 13.43), "13": (52.56, 13.35),
    "14": (52.40, 13.06), "15": (52.35, 14.05), "16": (52.76, 13.28), "17": (53.63, 13.30),
    "18": (54.09, 12.10), "19": (53.63, 11.41), "20": (53.55, 9.99), "21": (53.47, 9.78),
    "22": (53.60, 10.05), "23": (53.87, 10.69), "24": (54.32, 10.12), "25": (54.11, 9.13),
    "26": (53.14, 8.21), "27": (53.37, 8.62), "28": (53.08, 8.80), "29": (52.83, 9.45),
    "30": (52.37, 9.73), "31": (52.16, 9.95), "32": (52.02, 8.53), "33": (51.99, 8.59),
    "34": (51.31, 9.48), "35": (50.57, 8.67), "36": (50.55, 9.68), "37": (51.54, 9.92),
    "38": (52.26, 10.53), "39": (52.12, 11.63), "40": (51.23, 6.78), "41": (51.19, 6.44),
    "42": (51.26, 7.15), "44": (51.51, 7.47), "45": (51.46, 7.01), "46": (51.50, 6.86),
    "47": (51.43, 6.76), "48": (51.96, 7.63), "49": (52.28, 8.05), "50": (50.94, 6.96),
    "51": (51.05, 6.99), "52": (50.78, 6.08), "53": (50.74, 7.10), "54": (49.76, 6.64),
    "55": (50.00, 8.27), "56": (50.36, 7.59), "57": (50.87, 7.73), "58": (51.36, 7.47),
    "59": (51.68, 7.82), "60": (50.11, 8.68), "61": (50.22, 8.62), "63": (50.00, 9.00),
    "64": (49.87, 8.65), "65": (50.08, 8.24), "66": (49.24, 7.00), "67": (49.48, 8.45),
    "68": (49.49, 8.47), "69": (49.40, 8.67), "70": (48.78, 9.18), "71": (48.69, 9.01),
    "72": (48.52, 9.05), "73": (48.80, 9.49), "74": (49.14, 9.22), "75": (48.89, 8.70),
    "76": (49.01, 8.40), "77": (48.47, 8.21), "78": (47.76, 8.83), "79": (47.99, 7.84),
    "80": (48.14, 11.58), "81": (48.12, 11.60), "82": (48.05, 11.49), "83": (47.86, 12.13),
    "84": (48.46, 12.17), "85": (48.35, 11.79), "86": (48.37, 10.90), "87": (47.73, 10.31),
    "88": (47.72, 9.61), "89": (48.40, 10.00), "90": (49.45, 11.08), "91": (49.57, 10.96),
    "92": (49.32, 11.86), "93": (49.01, 12.10), "94": (48.57, 13.46), "95": (50.09, 11.91),
    "96": (50.27, 11.08), "97": (49.79, 9.93), "98": (50.69, 10.92), "99": (50.99, 11.03),
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in kilometers.

    Uses the Haversine formula for accurate Earth-surface distance calculation.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class PLZService:
    """
    Service for German postal code lookups and market data interpolation.

    Provides:
    - Bundesland lookup for any PLZ
    - Market data for major cities
    - Price interpolation for any PLZ based on nearest major city
    """

    def __init__(self):
        """Initialize the PLZ service."""
        self.cities = MAJOR_CITIES
        self.plz_to_bundesland = PLZ_PREFIX_TO_BUNDESLAND
        self.plz_coordinates = PLZ_PREFIX_COORDINATES

    def get_bundesland(self, plz: str) -> Optional[str]:
        """
        Get the Bundesland for a given PLZ.

        Args:
            plz: German postal code (5 digits as string)

        Returns:
            Bundesland name or None if not found
        """
        if not plz or len(plz) < 2:
            return None
        prefix = plz[:2]
        return self.plz_to_bundesland.get(prefix)

    def get_city_data(self, city_name: str) -> Optional[CityMarketData]:
        """
        Get market data for a specific city.

        Args:
            city_name: Name of the city

        Returns:
            CityMarketData or None if city not in database
        """
        return self.cities.get(city_name)

    def get_nearest_city(self, plz: str) -> Tuple[Optional[CityMarketData], float]:
        """
        Find the nearest major city to a given PLZ.

        Args:
            plz: German postal code

        Returns:
            Tuple of (nearest city data, distance in km)
        """
        if not plz or len(plz) < 2:
            return None, float('inf')

        prefix = plz[:2]

        # Get coordinates for this PLZ prefix
        if prefix not in self.plz_coordinates:
            return None, float('inf')

        plz_lat, plz_lon = self.plz_coordinates[prefix]

        # Find nearest city
        nearest_city = None
        min_distance = float('inf')

        for city_data in self.cities.values():
            distance = haversine_distance(
                plz_lat, plz_lon,
                city_data.latitude, city_data.longitude
            )
            if distance < min_distance:
                min_distance = distance
                nearest_city = city_data

        return nearest_city, min_distance

    def interpolate_market_data(
        self,
        plz: str,
        distance_discount_factor: float = 0.02
    ) -> Optional[Dict[str, float]]:
        """
        Interpolate market data for any PLZ based on nearest major city.

        Applies a distance-based discount: prices decrease ~2% per 10km from city center.

        Args:
            plz: German postal code
            distance_discount_factor: Price reduction per km (default 2% per 10km = 0.002/km)

        Returns:
            Dict with interpolated price_sqm and rent_sqm, or None
        """
        nearest_city, distance = self.get_nearest_city(plz)

        if nearest_city is None:
            return None

        # Apply distance discount (max 40% discount)
        discount = min(distance * distance_discount_factor / 10, 0.40)
        adjustment_factor = 1 - discount

        return {
            "city": nearest_city.name,
            "bundesland": nearest_city.bundesland,
            "distance_km": round(distance, 1),
            "price_sqm": round(nearest_city.avg_price_sqm * adjustment_factor, 0),
            "rent_sqm": round(nearest_city.avg_rent_sqm * adjustment_factor, 2),
            "adjustment_factor": round(adjustment_factor, 3),
        }

    def list_all_cities(self) -> list:
        """Return a sorted list of all cities in the database."""
        return sorted(self.cities.keys())

    def get_cities_by_bundesland(self, bundesland: str) -> list:
        """Get all cities in a specific Bundesland."""
        return [
            city_data for city_data in self.cities.values()
            if city_data.bundesland == bundesland
        ]


# Singleton instance
plz_service = PLZService()
