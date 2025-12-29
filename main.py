#!/usr/bin/env python3
"""
German Real Estate Investment Analysis System

Main entry point for running the application.

Usage:
    python main.py                    # Start the Streamlit dashboard
    python main.py --cli              # Run CLI analysis
    python main.py --demo             # Run demo analysis

Requirements:
    pip install -r requirements.txt
"""

import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def run_dashboard():
    """Start the Streamlit dashboard."""
    import subprocess
    dashboard_path = os.path.join(
        os.path.dirname(__file__),
        "src", "visualization", "dashboard.py"
    )
    subprocess.run(["streamlit", "run", dashboard_path])


def run_demo():
    """Run a demonstration analysis."""
    from src.analytics.crash_model import crash_model
    from src.analytics.dcf_model import dcf_model, PropertyInput
    from src.analytics.rate_forecast import rate_forecast_model
    from src.data_fetchers.market_data import market_data_fetcher
    from src.utils.helpers import format_currency

    print("\n" + "=" * 60)
    print("GERMAN REAL ESTATE INVESTMENT ANALYZER - DEMO")
    print("=" * 60)

    # 1. Market Overview
    print("\n📊 MARKTÜBERSICHT")
    print("-" * 40)

    crash_result = crash_model.calculate_crash_probability()
    print(f"Crash-Wahrscheinlichkeit: {crash_result.total_score:.0f}/100")
    print(f"Empfehlung: {crash_result.recommendation.value}")
    print(f"\n{crash_result.summary}")

    # 2. Rate Forecast
    print("\n📈 ZINSPROGNOSE")
    print("-" * 40)

    trajectory = rate_forecast_model.get_rate_trajectory_analysis()
    print(f"EZB-Leitzins aktuell: {trajectory.get('current_rate', 0):.2f}%")
    print(f"Zyklusphase: {trajectory.get('phase_description', 'Unbekannt')}")
    print(f"Implikation: {trajectory.get('implication', '')}")

    # 3. City Comparison
    print("\n🏙️ STÄDTEVERGLEICH")
    print("-" * 40)

    cities = ["muenchen", "berlin", "frankfurt", "hamburg"]
    comparison = market_data_fetcher.get_market_comparison(cities)
    print(comparison.to_string(index=False))

    # 4. Sample Investment Analysis
    print("\n💰 BEISPIEL-INVESTMENT")
    print("-" * 40)

    sample_property = PropertyInput(
        purchase_price=400000,
        sqm=80,
        property_type="Wohnung",
        plz="80331",
        city="muenchen",
        baujahr=2000,
        ltv=0.80,
        interest_rate=0.038,
        loan_term_years=20,
        initial_rent_sqm=18.0,
        holding_period_years=10
    )

    print(f"Objekt: {sample_property.sqm}qm {sample_property.property_type} in München")
    print(f"Kaufpreis: {format_currency(sample_property.purchase_price)}")
    print(f"LTV: {sample_property.ltv:.0%}")
    print(f"Zinssatz: {sample_property.interest_rate:.2%}")

    dcf_result = dcf_model.analyze_investment(sample_property)

    print(f"\nErgebnisse:")
    print(f"  IRR (nach Steuern): {dcf_result.base_case.metrics.irr_after_tax:.1%}")
    print(f"  NPV: {format_currency(dcf_result.base_case.metrics.npv)}")
    print(f"  Equity Multiple: {dcf_result.base_case.metrics.equity_multiple:.2f}x")
    print(f"  DSCR (Jahr 1): {dcf_result.base_case.metrics.dscr_year1:.2f}")
    print(f"\n  {dcf_result.recommendation}")

    print("\n" + "=" * 60)
    print("Demo abgeschlossen. Starten Sie 'python main.py' für das Dashboard.")
    print("=" * 60 + "\n")


def run_cli():
    """Run CLI analysis mode."""
    from src.analytics.crash_model import crash_model
    from src.data_fetchers.market_data import market_data_fetcher
    from src.utils.config import GERMAN_CITIES

    print("\n🏠 German Real Estate Investment Analyzer - CLI Mode")
    print("=" * 50)

    # Market Overview
    result = crash_model.calculate_crash_probability()
    print(f"\n📊 Crash-Score: {result.total_score:.0f}/100")
    print(f"   Empfehlung: {result.recommendation.value}")

    # City summary
    print("\n🏙️ Städte-Übersicht:")
    for city_key in list(GERMAN_CITIES.keys())[:5]:
        city_data = market_data_fetcher.get_city_market_data(city_key)
        if city_data:
            print(f"   {city_data.city_name}: €{city_data.avg_price_sqm:,.0f}/qm, "
                  f"Rendite: {city_data.gross_rental_yield:.1%}")

    print("\n✅ Für detaillierte Analyse starten Sie: python main.py")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="German Real Estate Investment Analysis System"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode (no dashboard)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration analysis"
    )

    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.cli:
        run_cli()
    else:
        run_dashboard()


if __name__ == "__main__":
    main()
