"""
Streamlit Dashboard for German Real Estate Investment Analysis.

Professional-grade interactive dashboard with:
1. Market Overview (Crash Probability)
2. Regional Analysis
3. Financial Model (DCF)
4. Rate Forecasts
5. Risk Analysis (Monte Carlo)
6. Data Explorer
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.analytics.crash_model import crash_model, CrashProbabilityResult
from src.analytics.dcf_model import dcf_model, PropertyInput, DCFAnalysisResult
from src.analytics.monte_carlo import monte_carlo_simulator, SimulationResult
from src.analytics.rate_forecast import rate_forecast_model
from src.data_fetchers.market_data import market_data_fetcher
from src.data_fetchers.destatis import destatis_fetcher
from src.visualization.charts import chart_factory
from src.visualization.maps import germany_map
from src.utils.config import config, GERMAN_CITIES, PropertyType, HeatingType, EnergyClass
from src.utils.helpers import format_currency, format_percentage


# Page configuration
st.set_page_config(
    page_title="German Real Estate Investment Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        border: 1px solid #e5e7eb;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the main header."""
    st.markdown('<p class="main-header">German Real Estate Investment Analyzer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Institutional-grade analysis for German residential real estate investments</p>', unsafe_allow_html=True)

    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)

    # Get current data
    try:
        rates = rate_forecast_model.get_rate_trajectory_analysis()
        current_ecb = rates.get("current_rate", 4.25)
        mortgage_rate = current_ecb + 2.0  # Approximate spread
    except Exception:
        current_ecb = 4.25
        mortgage_rate = 4.0

    crash_result = crash_model.calculate_crash_probability()

    with col1:
        st.metric("EZB-Leitzins", f"{current_ecb:.2f}%")
    with col2:
        st.metric("Hypothekenzins (ca.)", f"{mortgage_rate:.2f}%")
    with col3:
        st.metric("Crash-Score", f"{crash_result.total_score:.0f}/100")
    with col4:
        st.metric("Empfehlung", crash_result.recommendation.value)


def render_market_overview():
    """Render the Market Overview tab."""
    st.header("Marktübersicht")

    # Calculate crash probability
    city_filter = st.selectbox(
        "Stadt auswählen (optional)",
        options=["Deutschland (Gesamt)"] + [GERMAN_CITIES[k].name for k in GERMAN_CITIES.keys()],
        index=0
    )

    city_key = None
    if city_filter != "Deutschland (Gesamt)":
        city_key = [k for k, v in GERMAN_CITIES.items() if v.name == city_filter][0]

    with st.spinner("Berechne Crash-Wahrscheinlichkeit..."):
        result = crash_model.calculate_crash_probability(city_key)

    # Two columns: Gauge and Breakdown
    col1, col2 = st.columns([1, 1])

    with col1:
        # Crash probability gauge
        gauge = chart_factory.create_crash_gauge(
            result.total_score,
            result.recommendation.value
        )
        st.plotly_chart(gauge, use_container_width=True)

        # Summary
        st.info(result.summary)

    with col2:
        # Category breakdown
        categories = [
            {
                "name": cat.category,
                "score": cat.score,
                "weighted_score": cat.weighted_score,
                "status": cat.status
            }
            for cat in result.category_scores
        ]
        breakdown = chart_factory.create_category_breakdown(categories)
        st.plotly_chart(breakdown, use_container_width=True)

    # Key risks and positives
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Hauptrisiken")
        for risk in result.key_risks:
            st.warning(risk)

    with col2:
        st.subheader("Positive Faktoren")
        for positive in result.key_positives:
            st.success(positive)

    # House Price Index Chart
    st.subheader("Häuserpreisindex (HPI)")
    hpi_data = destatis_fetcher.get_house_price_index()
    if not hpi_data.empty:
        price_chart = chart_factory.create_price_chart(hpi_data, "Häuserpreisindex Deutschland (2015=100)")
        st.plotly_chart(price_chart, use_container_width=True)


def render_regional_analysis():
    """Render the Regional Analysis tab."""
    st.header("Regionale Analyse")

    # Map
    st.subheader("Marktübersicht Deutschland")

    try:
        market_map = germany_map.create_market_overview_map()
        map_html = germany_map.get_map_html(market_map)
        st.components.v1.html(map_html, height=500)
    except Exception as e:
        st.warning(f"Karte konnte nicht geladen werden: {e}")

    # City comparison
    st.subheader("Städtevergleich")

    selected_cities = st.multiselect(
        "Städte zum Vergleichen auswählen",
        options=list(GERMAN_CITIES.keys()),
        default=["muenchen", "berlin", "frankfurt", "hamburg"],
        format_func=lambda x: GERMAN_CITIES[x].name
    )

    if selected_cities:
        comparison_df = market_data_fetcher.get_market_comparison(selected_cities)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

        # Price comparison chart
        metric = st.selectbox("Metrik für Chart", options=["Preis/qm", "Miete/qm", "Arbeitslosigkeit"])
        comparison_chart = chart_factory.create_city_comparison_chart(
            comparison_df, metric, "Städtevergleich"
        )
        st.plotly_chart(comparison_chart, use_container_width=True)

    # City detail
    st.subheader("Stadt-Detail")
    selected_city = st.selectbox(
        "Stadt für Detailanalyse",
        options=list(GERMAN_CITIES.keys()),
        format_func=lambda x: GERMAN_CITIES[x].name
    )

    city_data = market_data_fetcher.get_city_market_data(selected_city)
    if city_data:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Preis/qm", format_currency(city_data.avg_price_sqm))
        with col2:
            st.metric("Miete/qm", f"€{city_data.avg_rent_sqm:.2f}")
        with col3:
            st.metric("Brutto-Rendite", f"{city_data.gross_rental_yield:.1%}")
        with col4:
            st.metric("P/R Ratio", f"{city_data.price_to_rent_ratio:.1f}x")

        # Market health score
        health = market_data_fetcher.get_market_health_score(selected_city)
        st.metric("Markt-Gesundheit", f"{health['score']:.0f}/100 ({health['status']})")


def render_financial_model():
    """Render the Financial Model tab."""
    st.header("Finanzmodell (DCF)")

    st.markdown("Analysieren Sie ein spezifisches Immobilien-Investment mit detaillierter Cash-Flow-Modellierung.")

    # Input form
    with st.form("property_form"):
        st.subheader("Objektdaten")

        col1, col2, col3 = st.columns(3)

        with col1:
            purchase_price = st.number_input(
                "Kaufpreis (EUR)",
                min_value=50000,
                max_value=10000000,
                value=400000,
                step=10000
            )
            sqm = st.number_input(
                "Wohnfläche (qm)",
                min_value=20,
                max_value=500,
                value=80,
                step=5
            )
            plz = st.text_input("Postleitzahl", value="80331")

        with col2:
            property_type = st.selectbox(
                "Objektart",
                options=["Wohnung", "Haus", "Mehrfamilienhaus"]
            )
            baujahr = st.number_input(
                "Baujahr",
                min_value=1900,
                max_value=2024,
                value=1990
            )
            heating = st.selectbox(
                "Heizungsart",
                options=["Gas", "Öl", "Fernwärme", "Wärmepumpe", "Pellet", "Elektro"]
            )

        with col3:
            condition = st.selectbox(
                "Zustand",
                options=["gut", "normal", "renovierungsbedürftig"]
            )
            energy_class = st.selectbox(
                "Energieeffizienzklasse",
                options=["A+", "A", "B", "C", "D", "E", "F", "G", "H"]
            )
            last_renovation = st.number_input(
                "Letzte Renovierung (Jahr)",
                min_value=1950,
                max_value=2024,
                value=2010
            )

        st.subheader("Finanzierung")

        col1, col2, col3 = st.columns(3)

        with col1:
            ltv = st.slider("Beleihungsquote (LTV)", 0.0, 1.0, 0.80, 0.05)
            interest_rate = st.slider("Zinssatz (%)", 1.0, 8.0, 3.8, 0.1) / 100

        with col2:
            loan_term = st.slider("Laufzeit (Jahre)", 5, 30, 20)
            rent_sqm = st.number_input(
                "Monatliche Miete/qm (EUR)",
                min_value=5.0,
                max_value=30.0,
                value=12.0,
                step=0.5
            )

        with col3:
            holding_period = st.slider("Haltedauer (Jahre)", 5, 30, 10)
            vacancy = st.slider("Leerstandsquote (%)", 0.0, 15.0, 3.0) / 100

        submitted = st.form_submit_button("Investment analysieren", use_container_width=True)

    if submitted:
        # Create property input
        property_input = PropertyInput(
            purchase_price=purchase_price,
            sqm=sqm,
            property_type=property_type,
            plz=plz,
            baujahr=baujahr,
            last_renovation=last_renovation,
            heating_type=heating,
            energy_class=energy_class,
            condition=condition,
            ltv=ltv,
            interest_rate=interest_rate,
            loan_term_years=loan_term,
            initial_rent_sqm=rent_sqm,
            vacancy_rate=vacancy,
            holding_period_years=holding_period
        )

        with st.spinner("Berechne DCF-Analyse..."):
            result = dcf_model.analyze_investment(property_input)

        # Display results
        st.subheader("Ergebnis")

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("IRR (nach Steuern)", f"{result.base_case.metrics.irr_after_tax:.1%}")
        with col2:
            st.metric("NPV (8% Hurdle)", format_currency(result.base_case.metrics.npv))
        with col3:
            st.metric("Equity Multiple", f"{result.base_case.metrics.equity_multiple:.2f}x")
        with col4:
            st.metric("DSCR (Jahr 1)", f"{result.base_case.metrics.dscr_year1:.2f}")

        # Recommendation
        if "EMPFEHLUNG" in result.recommendation or "STARKE" in result.recommendation:
            st.success(result.recommendation)
        elif "NEUTRAL" in result.recommendation:
            st.info(result.recommendation)
        else:
            st.warning(result.recommendation)

        # Scenario comparison
        st.subheader("Szenario-Vergleich")

        scenario_data = {
            "Szenario": ["Bear Case", "Base Case", "Bull Case"],
            "IRR": [
                f"{result.bear_case.metrics.irr_after_tax:.1%}" if result.bear_case else "-",
                f"{result.base_case.metrics.irr_after_tax:.1%}",
                f"{result.bull_case.metrics.irr_after_tax:.1%}" if result.bull_case else "-"
            ],
            "NPV": [
                format_currency(result.bear_case.metrics.npv) if result.bear_case else "-",
                format_currency(result.base_case.metrics.npv),
                format_currency(result.bull_case.metrics.npv) if result.bull_case else "-"
            ],
            "Equity Multiple": [
                f"{result.bear_case.metrics.equity_multiple:.2f}x" if result.bear_case else "-",
                f"{result.base_case.metrics.equity_multiple:.2f}x",
                f"{result.bull_case.metrics.equity_multiple:.2f}x" if result.bull_case else "-"
            ]
        }
        st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)

        # Cash flow chart
        if result.base_case.cash_flows:
            cf_data = [
                {"year": cf.year, "after_tax_cash_flow": cf.after_tax_cash_flow}
                for cf in result.base_case.cash_flows
            ]
            cf_chart = chart_factory.create_cashflow_waterfall(cf_data)
            st.plotly_chart(cf_chart, use_container_width=True)

        # Sensitivity analysis
        if result.sensitivity_analysis:
            st.subheader("Sensitivitätsanalyse")
            tornado = chart_factory.create_tornado_chart(result.sensitivity_analysis)
            st.plotly_chart(tornado, use_container_width=True)


def render_rate_forecasts():
    """Render the Rate Forecasts tab."""
    st.header("Zinsprognose")

    # Forecast horizon
    horizon = st.slider("Prognose-Horizont (Monate)", 6, 36, 24)

    with st.spinner("Erstelle Zinsprognose..."):
        # ECB rate forecast
        ecb_forecast = rate_forecast_model.forecast_ecb_rate(horizon)
        mortgage_forecast = rate_forecast_model.forecast_mortgage_rate(horizon)
        trajectory = rate_forecast_model.get_rate_trajectory_analysis()

    # Current status
    st.subheader("Aktuelle Zinssituation")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "EZB-Leitzins aktuell",
            f"{ecb_forecast.current_rate:.2f}%",
            delta=f"{trajectory.get('change_past_12m', 0):+.2f}% (12M)"
        )
    with col2:
        st.metric(
            "Hypothekenzins aktuell",
            f"{mortgage_forecast.current_rate:.2f}%"
        )
    with col3:
        st.info(f"**Zinszyklusphase:** {trajectory.get('phase_description', 'Unbekannt')}")

    # Forecast charts
    st.subheader("EZB-Zinsprognose")

    ecb_df = rate_forecast_model.to_dataframe(ecb_forecast)
    ecb_chart = chart_factory.create_rate_forecast_chart(
        ecb_df,
        ecb_forecast.current_rate,
        "EZB-Leitzins Prognose"
    )
    st.plotly_chart(ecb_chart, use_container_width=True)

    st.subheader("Hypothekenzins-Prognose")

    mortgage_df = rate_forecast_model.to_dataframe(mortgage_forecast)
    mortgage_chart = chart_factory.create_rate_forecast_chart(
        mortgage_df,
        mortgage_forecast.current_rate,
        "Hypothekenzins Prognose"
    )
    st.plotly_chart(mortgage_chart, use_container_width=True)

    # Methodology
    with st.expander("Methodik"):
        st.markdown(ecb_forecast.methodology_notes)

    # Investment implication
    st.subheader("Implikation für Immobilien-Investments")
    st.info(trajectory.get("implication", "Keine Einschätzung verfügbar"))


def render_risk_analysis():
    """Render the Risk Analysis tab."""
    st.header("Risiko-Analyse (Monte Carlo)")

    st.markdown("Stochastische Simulation zur Bewertung der Rendite-Verteilung und Risiko-Kennzahlen.")

    # Simulation parameters
    with st.expander("Simulationsparameter"):
        n_sims = st.slider("Anzahl Simulationen", 1000, 50000, 10000, 1000)
        rate_vol = st.slider("Zinsvolatilität (%)", 0.5, 3.0, 1.0, 0.1) / 100
        price_vol = st.slider("Preisvolatilität (%)", 3.0, 15.0, 8.0, 0.5) / 100

    # Property for simulation
    st.subheader("Objekt für Simulation")

    col1, col2, col3 = st.columns(3)

    with col1:
        sim_price = st.number_input("Kaufpreis", value=400000, step=10000)
        sim_sqm = st.number_input("Fläche (qm)", value=80)

    with col2:
        sim_ltv = st.slider("LTV", 0.5, 0.95, 0.8, 0.05)
        sim_rate = st.slider("Anfangszins (%)", 2.0, 6.0, 3.8, 0.1) / 100

    with col3:
        sim_holding = st.slider("Haltedauer", 5, 20, 10)

    if st.button("Monte Carlo Simulation starten", use_container_width=True):
        # Create base inputs
        base_inputs = PropertyInput(
            purchase_price=sim_price,
            sqm=sim_sqm,
            ltv=sim_ltv,
            interest_rate=sim_rate,
            holding_period_years=sim_holding,
            initial_rent_sqm=12.0
        )

        with st.spinner(f"Führe {n_sims:,} Simulationen durch..."):
            result = monte_carlo_simulator.run_simulation(base_inputs, n_sims)

        # Display results
        st.subheader("Simulationsergebnisse")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Erwartete IRR", f"{result.irr_mean:.1%}")
        with col2:
            st.metric("Std. Abweichung", f"{result.irr_std:.1%}")
        with col3:
            st.metric("Verlustwahrscheinlichkeit", f"{result.probability_of_loss:.1%}")
        with col4:
            st.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")

        # Distribution chart
        hist_chart = chart_factory.create_monte_carlo_histogram(
            result.irr_distribution,
            result.value_at_risk_5,
            result.irr_mean
        )
        st.plotly_chart(hist_chart, use_container_width=True)

        # Percentile table
        st.subheader("IRR Perzentile")
        percentile_data = {
            "Perzentil": [f"{p}%" for p in result.irr_percentiles.keys()],
            "IRR": [f"{v:.1%}" for v in result.irr_percentiles.values()]
        }
        st.dataframe(pd.DataFrame(percentile_data), use_container_width=True, hide_index=True)

        # Risk interpretation
        st.subheader("Risiko-Interpretation")
        if result.probability_of_loss < 0.05:
            st.success("**Niedriges Risiko:** Weniger als 5% Verlustwahrscheinlichkeit")
        elif result.probability_of_loss < 0.15:
            st.info("**Moderates Risiko:** 5-15% Verlustwahrscheinlichkeit")
        else:
            st.warning("**Erhöhtes Risiko:** Mehr als 15% Verlustwahrscheinlichkeit")


def render_data_explorer():
    """Render the Data Explorer tab."""
    st.header("Daten-Explorer")

    st.markdown("Zugriff auf Rohdaten und Export-Funktionen.")

    # Data source selection
    data_source = st.selectbox(
        "Datenquelle",
        options=["Marktdaten nach Stadt", "Häuserpreisindex", "Inflationsrate", "Bauprojekte"]
    )

    if data_source == "Marktdaten nach Stadt":
        all_cities = market_data_fetcher.get_all_cities_data()
        data = []
        for key, city in all_cities.items():
            data.append({
                "Stadt": city.city_name,
                "Preis/qm (EUR)": city.avg_price_sqm,
                "Miete/qm (EUR)": city.avg_rent_sqm,
                "Brutto-Rendite": f"{city.gross_rental_yield:.2%}",
                "P/R Ratio": city.price_to_rent_ratio,
                "P/I Ratio": city.price_to_income,
                "YoY Preis": f"{city.price_yoy_change:+.1f}%",
                "Leerstand (Mon.)": city.inventory_months,
                "Arbeitslosigkeit": f"{city.unemployment_rate:.1f}%"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    elif data_source == "Häuserpreisindex":
        hpi = destatis_fetcher.get_house_price_index()
        if not hpi.empty:
            hpi_df = hpi.reset_index()
            hpi_df.columns = ["Datum", "Index"]
            st.dataframe(hpi_df, use_container_width=True, hide_index=True)

    elif data_source == "Inflationsrate":
        cpi = destatis_fetcher.get_cpi()
        if not cpi.empty:
            inflation = cpi.pct_change(periods=12) * 100
            inflation_df = inflation.reset_index().dropna()
            inflation_df.columns = ["Datum", "Inflation (%)"]
            st.dataframe(inflation_df, use_container_width=True, hide_index=True)

    elif data_source == "Bauprojekte":
        permits = destatis_fetcher.get_building_permits()
        if not permits.empty:
            permits_df = permits.reset_index()
            permits_df.columns = ["Datum", "Genehmigungen"]
            st.dataframe(permits_df, use_container_width=True, hide_index=True)

    # Export button
    st.download_button(
        label="Als CSV exportieren",
        data=df.to_csv(index=False) if 'df' in dir() else "Keine Daten",
        file_name=f"immobilien_daten_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


def main():
    """Main dashboard function."""
    render_header()

    st.divider()

    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Marktübersicht",
        "🗺️ Regionale Analyse",
        "💰 Finanzmodell",
        "📈 Zinsprognose",
        "⚠️ Risiko-Analyse",
        "🔍 Daten-Explorer"
    ])

    with tab1:
        render_market_overview()

    with tab2:
        render_regional_analysis()

    with tab3:
        render_financial_model()

    with tab4:
        render_rate_forecasts()

    with tab5:
        render_risk_analysis()

    with tab6:
        render_data_explorer()

    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #6b7280; font-size: 0.8rem;">
        German Real Estate Investment Analyzer v1.0 | Daten zu Demonstrationszwecken<br>
        Keine Anlageberatung - Alle Investitionsentscheidungen auf eigenes Risiko
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
