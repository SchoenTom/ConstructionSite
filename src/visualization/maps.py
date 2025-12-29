"""
Geographic Visualization for German Real Estate Investment Analysis.

Creates interactive maps showing:
- City-level market data
- Regional risk indicators
- Price heat maps
"""

import folium
from folium import plugins
from typing import Dict, List, Optional, Any
import pandas as pd

from ..data_fetchers.market_data import market_data_fetcher
from ..utils.config import GERMAN_CITIES


# City coordinates (approximate city centers)
CITY_COORDINATES = {
    "muenchen": (48.1351, 11.5820),
    "berlin": (52.5200, 13.4050),
    "hamburg": (53.5511, 9.9937),
    "frankfurt": (50.1109, 8.6821),
    "koeln": (50.9375, 6.9603),
    "duesseldorf": (51.2277, 6.7735),
    "stuttgart": (48.7758, 9.1829),
    "leipzig": (51.3397, 12.3731),
    "dortmund": (51.5136, 7.4653),
    "nuernberg": (49.4521, 11.0767),
}

# Germany center for initial map view
GERMANY_CENTER = (51.1657, 10.4515)


class GermanyMap:
    """
    Creates interactive maps of German real estate markets.
    """

    def __init__(self):
        """Initialize map generator."""
        self.city_coords = CITY_COORDINATES

    def create_market_overview_map(
        self,
        show_prices: bool = True,
        show_risk: bool = True
    ) -> folium.Map:
        """
        Create an interactive map showing all cities with market data.

        Args:
            show_prices: Include price per sqm in tooltips
            show_risk: Color-code by market health

        Returns:
            Folium map object
        """
        # Create base map
        m = folium.Map(
            location=GERMANY_CENTER,
            zoom_start=6,
            tiles='CartoDB positron'
        )

        # Get market data for all cities
        all_cities = market_data_fetcher.get_all_cities_data()

        for city_key, coords in self.city_coords.items():
            city_data = all_cities.get(city_key)
            if not city_data:
                continue

            # Determine marker color based on price-to-rent ratio
            prr = city_data.price_to_rent_ratio
            if prr < 25:
                color = 'green'
                risk_level = 'Niedrig'
            elif prr < 30:
                color = 'orange'
                risk_level = 'Mittel'
            else:
                color = 'red'
                risk_level = 'Hoch'

            # Create popup content
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 200px;">
                <h4 style="margin-bottom: 10px;">{city_data.city_name}</h4>
                <table style="width: 100%; font-size: 12px;">
                    <tr>
                        <td><b>Preis/qm:</b></td>
                        <td>€{city_data.avg_price_sqm:,.0f}</td>
                    </tr>
                    <tr>
                        <td><b>Miete/qm:</b></td>
                        <td>€{city_data.avg_rent_sqm:.2f}</td>
                    </tr>
                    <tr>
                        <td><b>Rendite:</b></td>
                        <td>{city_data.gross_rental_yield:.1%}</td>
                    </tr>
                    <tr>
                        <td><b>P/R Ratio:</b></td>
                        <td>{city_data.price_to_rent_ratio:.1f}x</td>
                    </tr>
                    <tr>
                        <td><b>P/I Ratio:</b></td>
                        <td>{city_data.price_to_income:.1f}x</td>
                    </tr>
                    <tr>
                        <td><b>YoY Preis:</b></td>
                        <td>{city_data.price_yoy_change:+.1f}%</td>
                    </tr>
                    <tr>
                        <td><b>Risiko:</b></td>
                        <td style="color: {color};">{risk_level}</td>
                    </tr>
                </table>
            </div>
            """

            # Create marker
            folium.CircleMarker(
                location=coords,
                radius=15,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{city_data.city_name}: €{city_data.avg_price_sqm:,.0f}/qm",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)

            # Add city name label
            folium.Marker(
                location=coords,
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 10px; font-weight: bold; text-align: center;">{city_data.city_name}</div>',
                    icon_size=(100, 20),
                    icon_anchor=(50, -10)
                )
            ).add_to(m)

        # Add legend
        legend_html = """
        <div style="
            position: fixed;
            bottom: 50px;
            left: 50px;
            z-index: 1000;
            background-color: white;
            padding: 10px;
            border: 2px solid gray;
            border-radius: 5px;
            font-family: Arial, sans-serif;
            font-size: 12px;
        ">
            <b>Markt-Risiko</b><br>
            <i style="background:green;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Niedrig (P/R < 25)<br>
            <i style="background:orange;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Mittel (P/R 25-30)<br>
            <i style="background:red;width:12px;height:12px;display:inline-block;border-radius:50%;"></i> Hoch (P/R > 30)
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        return m

    def create_price_heatmap(self) -> folium.Map:
        """
        Create a heat map showing price intensity.

        Returns:
            Folium map with heat layer
        """
        m = folium.Map(
            location=GERMANY_CENTER,
            zoom_start=6,
            tiles='CartoDB positron'
        )

        # Get market data
        all_cities = market_data_fetcher.get_all_cities_data()

        # Prepare heat data - weighted by price
        heat_data = []
        for city_key, coords in self.city_coords.items():
            city_data = all_cities.get(city_key)
            if city_data:
                # Weight by price (normalized)
                weight = city_data.avg_price_sqm / 10000
                heat_data.append([coords[0], coords[1], weight])

        # Add heat layer
        plugins.HeatMap(
            heat_data,
            min_opacity=0.3,
            radius=50,
            blur=30,
            gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 1: 'red'}
        ).add_to(m)

        return m

    def create_city_detail_map(
        self,
        city_key: str
    ) -> folium.Map:
        """
        Create a detailed map for a specific city.

        Args:
            city_key: City identifier

        Returns:
            Folium map focused on the city
        """
        coords = self.city_coords.get(city_key, GERMANY_CENTER)
        city_data = market_data_fetcher.get_city_market_data(city_key)

        m = folium.Map(
            location=coords,
            zoom_start=12,
            tiles='CartoDB positron'
        )

        if city_data:
            # Add city center marker
            folium.Marker(
                location=coords,
                popup=f"""
                <b>{city_data.city_name}</b><br>
                Preis: €{city_data.avg_price_sqm:,.0f}/qm<br>
                Miete: €{city_data.avg_rent_sqm:.2f}/qm<br>
                Rendite: {city_data.gross_rental_yield:.1%}
                """,
                icon=folium.Icon(color='blue', icon='home')
            ).add_to(m)

        return m

    def get_map_html(self, m: folium.Map) -> str:
        """
        Convert Folium map to HTML string for embedding.

        Args:
            m: Folium map object

        Returns:
            HTML string
        """
        return m._repr_html_()


# Singleton instance
germany_map = GermanyMap()
