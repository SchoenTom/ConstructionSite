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
    st.markdown('<p class="main-header">Immobilien-Investment-Analysator für Deutschland</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professionelle Analyse für deutsche Wohnimmobilien-Investments</p>', unsafe_allow_html=True)

    # Quick stats row with explanations
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

    # Translation for recommendations
    rec_translations = {
        "STRONG_BUY": "Stark Kaufen",
        "BUY": "Kaufen",
        "HOLD": "Halten",
        "CAUTION": "Vorsicht",
        "AVOID": "Meiden"
    }

    with col1:
        st.metric(
            "EZB-Leitzins",
            f"{current_ecb:.2f}%",
            help="Der aktuelle Hauptrefinanzierungssatz der Europäischen Zentralbank."
        )
    with col2:
        st.metric(
            "Typischer Hypothekenzins",
            f"{mortgage_rate:.2f}%",
            help="Ungefährer aktueller Zinssatz für 10-jährige Immobilienkredite."
        )
    with col3:
        st.metric(
            "Marktrisiko-Score",
            f"{crash_result.total_score:.0f}/100",
            help="Crash-Wahrscheinlichkeit: 0 = sehr niedrig, 100 = sehr hoch."
        )
    with col4:
        st.metric(
            "Markt-Empfehlung",
            rec_translations.get(crash_result.recommendation.value, crash_result.recommendation.value),
            help="Aktuelle Empfehlung basierend auf der Marktbewertung."
        )


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

    st.markdown("""
    Diese Seite ermöglicht Ihnen den Vergleich verschiedener deutscher Städte hinsichtlich
    ihrer Immobilienmärkte. Wählen Sie Städte aus, um Preise, Mieten und Marktbedingungen
    zu vergleichen.
    """)

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

    st.info(f"**{len(GERMAN_CITIES)} deutsche Städte verfügbar** - Wählen Sie Städte zum Vergleichen aus.")

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
        metric = st.selectbox(
            "Metrik für Chart",
            options=["Preis pro Quadratmeter", "Miete pro Quadratmeter", "Arbeitslosenquote"],
            format_func=lambda x: x
        )

        # Map display names to data columns
        metric_map = {
            "Preis pro Quadratmeter": "Preis/qm",
            "Miete pro Quadratmeter": "Miete/qm",
            "Arbeitslosenquote": "Arbeitslosigkeit"
        }
        comparison_chart = chart_factory.create_city_comparison_chart(
            comparison_df, metric_map.get(metric, metric), "Städtevergleich"
        )
        st.plotly_chart(comparison_chart, use_container_width=True)

    # City detail
    st.subheader("Stadt-Detailanalyse")

    # Search functionality for cities
    search_term = st.text_input("Stadt suchen (z.B. Konstanz, München, Berlin):", "")

    # Filter cities based on search
    if search_term:
        filtered_cities = [k for k, v in GERMAN_CITIES.items()
                         if search_term.lower() in v.name.lower()]
        if not filtered_cities:
            st.warning(f"Keine Stadt gefunden für '{search_term}'")
            filtered_cities = list(GERMAN_CITIES.keys())
    else:
        filtered_cities = list(GERMAN_CITIES.keys())

    selected_city = st.selectbox(
        "Stadt für Detailanalyse auswählen",
        options=filtered_cities,
        format_func=lambda x: f"{GERMAN_CITIES[x].name} ({GERMAN_CITIES[x].state})"
    )

    city_data = market_data_fetcher.get_city_market_data(selected_city)
    if city_data:
        st.markdown(f"### {city_data.city_name}")
        st.markdown(f"*{GERMAN_CITIES[selected_city].state} | Einwohner: {GERMAN_CITIES[selected_city].population:,}*")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Kaufpreis pro Quadratmeter", format_currency(city_data.avg_price_sqm))
        with col2:
            st.metric("Monatsmiete pro Quadratmeter", f"€{city_data.avg_rent_sqm:.2f}")
        with col3:
            st.metric("Bruttomietrendite", f"{city_data.gross_rental_yield:.1%}")
        with col4:
            st.metric("Preis-zu-Miete-Verhältnis", f"{city_data.price_to_rent_ratio:.1f} Jahre")

        # Market health score with explanation
        health = market_data_fetcher.get_market_health_score(selected_city)

        status_translations = {
            "healthy": "Gesund",
            "moderate": "Moderat",
            "caution": "Vorsicht",
            "high_risk": "Hohes Risiko"
        }

        st.metric("Markt-Gesundheitsbewertung", f"{health['score']:.0f}/100 ({status_translations.get(health['status'], health['status'])})")

        # Interpretation
        st.markdown("#### Interpretation")
        if health['score'] >= 70:
            st.success("""
            **Gesunder Markt**: Die Bewertungskennzahlen liegen im normalen Bereich.
            Das Verhältnis von Kaufpreisen zu Mieten und Einkommen ist nachhaltig.
            Gute Bedingungen für langfristige Investments.
            """)
        elif health['score'] >= 50:
            st.info("""
            **Moderater Markt**: Einige Kennzahlen zeigen Auffälligkeiten.
            Der Markt ist weder unterbewertet noch stark überbewertet.
            Sorgfältige Objektauswahl empfohlen.
            """)
        elif health['score'] >= 30:
            st.warning("""
            **Markt mit Vorsicht zu betrachten**: Mehrere Indikatoren zeigen Überbewertung.
            Hohe Kaufpreise relativ zu Mieten und Einkommen.
            Nur bei überdurchschnittlichen Objekten investieren.
            """)
        else:
            st.error("""
            **Hohes Marktrisiko**: Starke Überbewertung erkennbar.
            Kaufpreise stehen in keinem gesunden Verhältnis zu den Fundamentaldaten.
            Abwarten oder sehr selektiv investieren empfohlen.
            """)


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
            ltv = st.slider(
                "Beleihungsquote (Fremdkapitalanteil)",
                0.0, 1.0, 0.80, 0.05,
                help="Der Anteil des Kaufpreises, der durch einen Kredit finanziert wird. 80% bedeutet: 80% Kredit, 20% Eigenkapital."
            )
            interest_rate = st.slider(
                "Darlehenszinssatz (Prozent pro Jahr)",
                1.0, 8.0, 3.8, 0.1,
                help="Der jährliche Zinssatz für Ihr Immobiliendarlehen."
            ) / 100

        with col2:
            loan_term = st.slider(
                "Kreditlaufzeit (Jahre)",
                5, 30, 20,
                help="Die Laufzeit Ihres Immobilienkredits in Jahren."
            )
            rent_sqm = st.number_input(
                "Monatliche Kaltmiete pro Quadratmeter (Euro)",
                min_value=5.0,
                max_value=30.0,
                value=12.0,
                step=0.5,
                help="Die erwartete Nettokaltmiete pro Quadratmeter und Monat."
            )

        with col3:
            holding_period = st.slider(
                "Geplante Haltedauer (Jahre)",
                5, 30, 10,
                help="Wie lange Sie die Immobilie halten möchten. Nach 10 Jahren entfällt in Deutschland die Spekulationssteuer."
            )
            vacancy = st.slider(
                "Erwartete Leerstandsquote (Prozent)",
                0.0, 15.0, 3.0,
                help="Durchschnittlicher Anteil der Zeit ohne Mieteinnahmen (z.B. bei Mieterwechsel)."
            ) / 100

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
        st.subheader("Analyseergebnis")

        # Key metrics with explanations
        st.markdown("#### Wichtige Kennzahlen")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Interne Rendite (nach Steuern)",
                f"{result.base_case.metrics.irr_after_tax:.1%}",
                help="Die durchschnittliche jährliche Rendite Ihres eingesetzten Kapitals über die Haltedauer."
            )
        with col2:
            st.metric(
                "Kapitalwert (bei 8% Zielrendite)",
                format_currency(result.base_case.metrics.npv),
                help="Der heutige Wert aller zukünftigen Zahlungsströme. Positiv = Investment schlägt 8% Zielrendite."
            )
        with col3:
            st.metric(
                "Eigenkapital-Vervielfacher",
                f"{result.base_case.metrics.equity_multiple:.2f}x",
                help="Wie oft Sie Ihr eingesetztes Eigenkapital zurückbekommen. 2.0x = Verdopplung."
            )
        with col4:
            st.metric(
                "Schuldendienstdeckung (Jahr 1)",
                f"{result.base_case.metrics.dscr_year1:.2f}",
                help="Verhältnis von Mieteinnahmen zu Kreditrate. Über 1.2 gilt als sicher."
            )

        # Interpretation
        st.markdown("#### Interpretation der Ergebnisse")

        irr = result.base_case.metrics.irr_after_tax
        npv = result.base_case.metrics.npv
        dscr = result.base_case.metrics.dscr_year1

        if irr >= 0.08 and npv > 0 and dscr >= 1.2:
            st.success(f"""
            **Attraktives Investment**: Mit einer internen Rendite von {irr:.1%} übertrifft dieses Investment
            die Zielrendite von 8%. Der positive Kapitalwert von {format_currency(npv)} zeigt, dass Sie
            nach Berücksichtigung aller Kosten und Steuern einen Vermögenszuwachs erzielen.
            Die Schuldendienstdeckung von {dscr:.2f} bedeutet, dass die Mieteinnahmen die Kreditrate
            um {(dscr-1)*100:.0f}% übersteigen - ein guter Sicherheitspuffer.
            """)
        elif irr >= 0.05:
            st.info(f"""
            **Solides Investment**: Die interne Rendite von {irr:.1%} liegt im akzeptablen Bereich.
            Das Investment ist rentabel, bietet aber nur begrenzten Puffer gegen unvorhergesehene Kosten.
            Prüfen Sie, ob bessere Konditionen (niedrigerer Kaufpreis, höhere Miete) erreichbar sind.
            """)
        elif irr >= 0:
            st.warning(f"""
            **Grenzwertiges Investment**: Mit nur {irr:.1%} interner Rendite ist die Rentabilität gering.
            Nach Berücksichtigung aller Risiken könnte dieses Investment enttäuschen.
            Verhandeln Sie einen niedrigeren Kaufpreis oder suchen Sie nach Alternativen.
            """)
        else:
            st.error(f"""
            **Nicht empfehlenswert**: Die negative Rendite von {irr:.1%} zeigt, dass dieses Investment
            Geld kostet statt einbringt. Der Kaufpreis ist zu hoch für die erzielbaren Mieteinnahmen.
            Von diesem Investment wird abgeraten.
            """)

        # Recommendation
        st.markdown("#### Empfehlung")
        if "EMPFEHLUNG" in result.recommendation or "STARKE" in result.recommendation:
            st.success(result.recommendation)
        elif "NEUTRAL" in result.recommendation:
            st.info(result.recommendation)
        else:
            st.warning(result.recommendation)

        # Scenario comparison
        st.subheader("Szenario-Vergleich")

        st.markdown("""
        Die folgende Tabelle zeigt drei Szenarien:
        - **Pessimistisches Szenario**: Ungünstige Marktentwicklung (sinkende Preise, steigende Zinsen)
        - **Basisszenario**: Wahrscheinlichste Entwicklung basierend auf aktuellen Trends
        - **Optimistisches Szenario**: Günstige Marktentwicklung (steigende Preise, stabile Zinsen)
        """)

        scenario_data = {
            "Szenario": ["Pessimistisch", "Basis", "Optimistisch"],
            "Interne Rendite": [
                f"{result.bear_case.metrics.irr_after_tax:.1%}" if result.bear_case else "-",
                f"{result.base_case.metrics.irr_after_tax:.1%}",
                f"{result.bull_case.metrics.irr_after_tax:.1%}" if result.bull_case else "-"
            ],
            "Kapitalwert": [
                format_currency(result.bear_case.metrics.npv) if result.bear_case else "-",
                format_currency(result.base_case.metrics.npv),
                format_currency(result.bull_case.metrics.npv) if result.bull_case else "-"
            ],
            "Eigenkapital-Vervielfacher": [
                f"{result.bear_case.metrics.equity_multiple:.2f}x" if result.bear_case else "-",
                f"{result.base_case.metrics.equity_multiple:.2f}x",
                f"{result.bull_case.metrics.equity_multiple:.2f}x" if result.bull_case else "-"
            ]
        }
        st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)

        # Cash flow chart with detailed explanation
        if result.base_case.cash_flows:
            st.subheader("Jährliche Cashflow-Analyse")

            # Explanation of what cash flow consists of
            with st.expander("Was ist der Cashflow und wie wird er berechnet?", expanded=False):
                st.markdown("""
                #### Bestandteile des jährlichen Cashflows

                Der **Cashflow nach Steuern** zeigt, wie viel Geld Sie tatsächlich jedes Jahr aus dem Investment erhalten (oder zuschießen müssen).

                **Berechnung Schritt für Schritt:**

                | Komponente | Beschreibung |
                |------------|--------------|
                | **+ Bruttomieteinnahmen** | Monatliche Kaltmiete × 12 Monate |
                | **− Leerstandsverlust** | Geschätzter Mietausfall bei Mieterwechsel (ca. 3-5%) |
                | **= Effektive Mieteinnahmen** | Was tatsächlich an Miete eingeht |
                | **− Nicht-umlagefähige Nebenkosten** | Kosten, die nicht auf den Mieter umgelegt werden können |
                | **− Hausverwaltung** | Kosten für die Verwaltung (ca. 20-25€/Einheit/Monat) |
                | **− Instandhaltungsrücklage** | Rücklage für Reparaturen (ca. 1% des Gebäudewerts/Jahr) |
                | **= Netto-Betriebsergebnis** | Einnahmen nach allen Betriebskosten |
                | **− Zinszahlung** | Zinsen für das Darlehen |
                | **− Tilgung** | Rückzahlung des Darlehens |
                | **= Cashflow vor Steuern** | |
                | **± Steuereffekt** | Einkommensteuer auf Mietüberschuss, ABER: AfA-Abschreibung (2-3% des Gebäudewerts) mindert die Steuerlast erheblich! |
                | **= Cashflow nach Steuern** | **Das ist Ihr tatsächlicher jährlicher Überschuss (oder Zuschuss)** |

                **Legende im Diagramm:**
                - 🟢 **Grüne Balken** = Positiver Cashflow (Sie erhalten Geld)
                - 🔴 **Rote Balken** = Negativer Cashflow (Sie müssen Geld zuschießen)

                **Hinweis:** Ein negativer Cashflow in den ersten Jahren ist nicht ungewöhnlich, besonders bei hoher Tilgung.
                Die Tilgung baut Eigenkapital auf und ist keine "verlorene" Ausgabe!
                """)

            cf_data = [
                {"year": cf.year, "after_tax_cash_flow": cf.after_tax_cash_flow}
                for cf in result.base_case.cash_flows
            ]
            cf_chart = chart_factory.create_cashflow_waterfall(cf_data)
            st.plotly_chart(cf_chart, use_container_width=True)

            # Additional context about the cash flow
            total_cf = sum(cf.after_tax_cash_flow for cf in result.base_case.cash_flows)
            avg_cf = total_cf / len(result.base_case.cash_flows) if result.base_case.cash_flows else 0
            positive_years = sum(1 for cf in result.base_case.cash_flows if cf.after_tax_cash_flow > 0)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Gesamter Cashflow",
                    f"€{total_cf:,.0f}",
                    help="Summe aller jährlichen Cashflows über die Haltedauer"
                )
            with col2:
                st.metric(
                    "Durchschnittlicher Cashflow pro Jahr",
                    f"€{avg_cf:,.0f}",
                    help="Durchschnittlicher jährlicher Cashflow"
                )
            with col3:
                st.metric(
                    "Jahre mit positivem Cashflow",
                    f"{positive_years} von {len(result.base_case.cash_flows)}",
                    help="Anzahl der Jahre mit Überschuss"
                )

        # Sensitivity analysis
        if result.sensitivity_analysis:
            st.subheader("Sensitivitätsanalyse")
            tornado = chart_factory.create_tornado_chart(result.sensitivity_analysis)
            st.plotly_chart(tornado, use_container_width=True)


def render_rate_forecasts():
    """Render the Rate Forecasts tab."""
    st.header("Zinsentwicklung und Prognose")

    st.markdown("""
    Diese Seite zeigt die aktuelle Zinssituation und Prognosen für die kommenden Monate.
    Die Zinsentwicklung ist einer der wichtigsten Faktoren für Immobilieninvestments,
    da sie sowohl die Finanzierungskosten als auch die Immobilienpreise beeinflusst.
    """)

    # Forecast horizon
    horizon = st.slider(
        "Prognose-Zeitraum auswählen (Monate)",
        6, 36, 24,
        help="Wie weit in die Zukunft soll die Prognose reichen?"
    )

    with st.spinner("Berechne Zinsprognose..."):
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
            delta=f"{trajectory.get('change_past_12m', 0):+.2f}% (letzte 12 Monate)",
            help="Der Hauptrefinanzierungssatz der Europäischen Zentralbank."
        )
    with col2:
        st.metric(
            "Hypothekenzins aktuell",
            f"{mortgage_forecast.current_rate:.2f}%",
            help="Typischer Zinssatz für 10-jährige Immobiliendarlehen."
        )
    with col3:
        st.info(f"**Aktuelle Zinsphase:** {trajectory.get('phase_description', 'Unbekannt')}")

    # Explanation of current phase
    st.markdown("#### Was bedeutet das für Immobilienkäufer?")

    current_rate = ecb_forecast.current_rate
    if current_rate >= 4.0:
        st.warning("""
        **Hochzinsphase**: Die Zinsen sind auf einem hohen Niveau. Das bedeutet:
        - Finanzierungskosten sind erhöht
        - Immobilienpreise stehen unter Druck
        - Gute Verhandlungsposition für Käufer
        - Langfristige Zinsbindung kann sich lohnen, wenn Zinssenkungen erwartet werden
        """)
    elif current_rate >= 2.5:
        st.info("""
        **Moderate Zinsphase**: Die Zinsen liegen im mittleren Bereich. Das bedeutet:
        - Normale Finanzierungskosten
        - Ausgewogener Markt zwischen Käufern und Verkäufern
        - Sowohl kurz- als auch langfristige Zinsbindung kann sinnvoll sein
        """)
    else:
        st.success("""
        **Niedrigzinsphase**: Die Zinsen sind historisch niedrig. Das bedeutet:
        - Günstige Finanzierungskosten
        - Langfristige Zinsbindung empfohlen
        - Hohe Nachfrage kann zu Preissteigerungen führen
        """)

    # Forecast charts
    st.subheader("Prognose: EZB-Leitzins")

    ecb_df = rate_forecast_model.to_dataframe(ecb_forecast)
    ecb_chart = chart_factory.create_rate_forecast_chart(
        ecb_df,
        ecb_forecast.current_rate,
        "EZB-Leitzins Prognose"
    )
    st.plotly_chart(ecb_chart, use_container_width=True)

    st.subheader("Prognose: Hypothekenzins")

    mortgage_df = rate_forecast_model.to_dataframe(mortgage_forecast)
    mortgage_chart = chart_factory.create_rate_forecast_chart(
        mortgage_df,
        mortgage_forecast.current_rate,
        "Hypothekenzins Prognose (10 Jahre Zinsbindung)"
    )
    st.plotly_chart(mortgage_chart, use_container_width=True)

    # Methodology
    with st.expander("Wie wird die Prognose berechnet?"):
        st.markdown("""
        Die Zinsprognose basiert auf mehreren Faktoren:

        1. **Markt-implizite Forward-Rates**: Was der Markt für zukünftige Zinsen erwartet
        2. **Taylor-Regel**: Berechnung basierend auf Inflation und Wirtschaftswachstum
        3. **Historische Muster**: Wie sich Zinsen in ähnlichen Situationen entwickelt haben

        **Wichtiger Hinweis:** Zinsprognosen sind mit erheblicher Unsicherheit behaftet.
        Die tatsächliche Entwicklung kann deutlich abweichen.
        """)
        st.markdown(ecb_forecast.methodology_notes)

    # Investment implication
    st.subheader("Handlungsempfehlung für Ihr Investment")

    implication = trajectory.get("implication", "Keine Einschätzung verfügbar")

    if "sinkend" in implication.lower() or "fallend" in implication.lower():
        st.success(f"""
        **Positive Zinsaussichten**

        {implication}

        **Empfehlung:**
        - Kurzfristige Zinsbindung kann vorteilhaft sein
        - Möglichkeit zur späteren Refinanzierung zu niedrigeren Zinsen
        - Immobilienpreise könnten bei sinkenden Zinsen steigen
        """)
    elif "steigend" in implication.lower():
        st.warning(f"""
        **Herausfordernde Zinsaussichten**

        {implication}

        **Empfehlung:**
        - Langfristige Zinsbindung sichert aktuelle Konditionen
        - Puffer für steigende Raten einplanen
        - Verhandlungsspielraum beim Kaufpreis nutzen
        """)
    else:
        st.info(f"""
        **Stabile Zinsaussichten**

        {implication}

        **Empfehlung:**
        - Mittelfristige Zinsbindung (10-15 Jahre) oft optimal
        - Aktuelle Konditionen sind marktüblich
        - Fokus auf Objektqualität und Lage wichtiger als Timing
        """)


def render_risk_analysis():
    """Render the Risk Analysis tab."""
    st.header("Risiko-Analyse (Monte Carlo Simulation)")

    st.markdown("""
    ### Was ist eine Monte Carlo Simulation?

    Die Monte Carlo Simulation berechnet tausende mögliche Zukunftsszenarien für Ihr Investment.
    Dabei werden zufällige Schwankungen bei Zinsen, Immobilienpreisen und Mieten berücksichtigt.
    Das Ergebnis zeigt Ihnen, wie wahrscheinlich verschiedene Renditen sind und wie hoch
    Ihr Verlustrisiko ist.

    **Wichtig:** Je mehr Informationen Sie eingeben, desto genauer wird die Simulation.
    Alle Felder sind optional - nicht ausgefüllte Felder verwenden realistische Standardwerte.
    """)

    st.divider()

    # Required inputs
    st.subheader("Grunddaten des Objekts")
    st.markdown("*Mindestens Kaufpreis und Wohnfläche werden für die Simulation benötigt.*")

    col1, col2 = st.columns(2)

    with col1:
        sim_price = st.number_input(
            "Kaufpreis (Euro) *",
            value=400000,
            step=10000,
            min_value=50000,
            help="Der geplante Kaufpreis der Immobilie inkl. Kaufnebenkosten."
        )
        sim_sqm = st.number_input(
            "Wohnfläche (Quadratmeter) *",
            value=80,
            min_value=20,
            help="Die Wohnfläche der Immobilie in Quadratmetern."
        )

    with col2:
        sim_holding = st.slider(
            "Geplante Haltedauer (Jahre) *",
            5, 25, 10,
            help="Wie lange Sie die Immobilie halten möchten."
        )

    # Optional financing inputs
    st.subheader("Finanzierungsdaten (optional)")
    st.markdown("*Wenn Sie diese Daten nicht angeben, werden typische Marktkonditionen verwendet.*")

    use_custom_financing = st.checkbox("Eigene Finanzierungskonditionen eingeben", value=False)

    if use_custom_financing:
        col1, col2 = st.columns(2)
        with col1:
            sim_ltv = st.slider(
                "Fremdkapitalanteil (Beleihungsquote)",
                0.5, 0.95, 0.8, 0.05,
                help="Der Anteil des Kaufpreises, der finanziert wird. Standard: 80%."
            )
            sim_rate = st.slider(
                "Aktueller Darlehenszins (Prozent pro Jahr)",
                2.0, 7.0, 3.8, 0.1,
                help="Ihr aktueller oder erwarteter Zinssatz."
            ) / 100
        with col2:
            sim_rent = st.number_input(
                "Monatliche Kaltmiete pro Quadratmeter (Euro)",
                min_value=5.0,
                max_value=25.0,
                value=12.0,
                step=0.5,
                help="Die erwartete oder aktuelle Nettokaltmiete."
            )
    else:
        sim_ltv = 0.8  # Standard
        sim_rate = 0.038  # Standard 3.8%
        sim_rent = 12.0  # Standard

    # Optional advanced parameters
    st.subheader("Erweiterte Simulationsparameter (optional)")
    st.markdown("*Für fortgeschrittene Nutzer. Standardwerte basieren auf historischen Marktdaten.*")

    use_advanced = st.checkbox("Erweiterte Parameter anpassen", value=False)

    if use_advanced:
        col1, col2, col3 = st.columns(3)

        with col1:
            n_sims = st.slider(
                "Anzahl Simulationsdurchläufe",
                1000, 50000, 10000, 1000,
                help="Mehr Durchläufe = genauere Ergebnisse, aber längere Rechenzeit."
            )

        with col2:
            rate_vol = st.slider(
                "Erwartete Zinsschwankung (Prozent pro Jahr)",
                0.5, 3.0, 1.0, 0.1,
                help="Wie stark die Zinsen schwanken könnten. Historisch: ca. 1%."
            ) / 100

        with col3:
            price_vol = st.slider(
                "Erwartete Preisschwankung (Prozent pro Jahr)",
                3.0, 15.0, 8.0, 0.5,
                help="Wie stark die Immobilienpreise schwanken könnten. Historisch: ca. 8%."
            ) / 100
    else:
        n_sims = 10000
        rate_vol = 0.01
        price_vol = 0.08

    st.divider()

    if st.button("Risiko-Simulation starten", use_container_width=True, type="primary"):
        # Create base inputs
        base_inputs = PropertyInput(
            purchase_price=sim_price,
            sqm=sim_sqm,
            ltv=sim_ltv,
            interest_rate=sim_rate,
            holding_period_years=sim_holding,
            initial_rent_sqm=sim_rent
        )

        with st.spinner(f"Berechne {n_sims:,} mögliche Zukunftsszenarien..."):
            result = monte_carlo_simulator.run_simulation(base_inputs, n_sims)

        # Display results with explanations
        st.subheader("Ergebnisse der Risiko-Simulation")

        st.markdown("""
        Die Simulation hat tausende mögliche Entwicklungen Ihres Investments berechnet.
        Hier sehen Sie die wichtigsten Erkenntnisse:
        """)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Erwartete Rendite",
                f"{result.irr_mean:.1%}",
                help="Der Durchschnitt aller simulierten Renditen - Ihr wahrscheinlichstes Ergebnis."
            )
        with col2:
            st.metric(
                "Schwankungsbreite",
                f"±{result.irr_std:.1%}",
                help="Wie stark die Rendite vom Durchschnitt abweichen könnte. Kleiner = stabiler."
            )
        with col3:
            st.metric(
                "Verlustrisiko",
                f"{result.probability_of_loss:.1%}",
                help="In wie vielen Szenarien Sie Geld verlieren würden."
            )
        with col4:
            st.metric(
                "Risiko-Rendite-Verhältnis",
                f"{result.sharpe_ratio:.2f}",
                help="Je höher, desto besser ist das Verhältnis von Rendite zu Risiko. Über 1.0 gilt als gut."
            )

        # Distribution chart
        st.markdown("#### Verteilung der möglichen Renditen")
        st.markdown("""
        Das folgende Diagramm zeigt, wie wahrscheinlich verschiedene Renditen sind.
        Die rote Linie markiert das 5%-Risiko (nur 5% der Szenarien sind schlechter).
        """)

        hist_chart = chart_factory.create_monte_carlo_histogram(
            result.irr_distribution,
            result.value_at_risk_5,
            result.irr_mean
        )
        st.plotly_chart(hist_chart, use_container_width=True)

        # Percentile table with explanations
        st.markdown("#### Rendite-Wahrscheinlichkeiten")
        st.markdown("""
        Diese Tabelle zeigt, welche Rendite Sie mit welcher Wahrscheinlichkeit erreichen:
        """)

        percentile_explanations = {
            5: "Schlechtester Fall (nur 5% sind schlechter)",
            10: "Ungünstiges Szenario",
            25: "Unterdurchschnittliches Ergebnis",
            50: "Mittleres Ergebnis (genauso wahrscheinlich besser wie schlechter)",
            75: "Überdurchschnittliches Ergebnis",
            90: "Günstiges Szenario",
            95: "Bester Fall (nur 5% sind besser)"
        }

        percentile_data = {
            "Szenario": [percentile_explanations[p] for p in result.irr_percentiles.keys()],
            "Wahrscheinlichkeit": [f"{p}%" for p in result.irr_percentiles.keys()],
            "Rendite": [f"{v:.1%}" for v in result.irr_percentiles.values()]
        }
        st.dataframe(pd.DataFrame(percentile_data), use_container_width=True, hide_index=True)

        # Detailed interpretation and recommendations
        st.markdown("#### Interpretation und Empfehlung")

        prob_loss = result.probability_of_loss
        irr_mean = result.irr_mean
        sharpe = result.sharpe_ratio
        var_5 = result.value_at_risk_5

        if prob_loss < 0.05 and irr_mean >= 0.06:
            st.success(f"""
            **Empfehlung: Attraktives Investment mit niedrigem Risiko**

            ✅ **Verlustrisiko sehr gering** ({prob_loss:.0%}): In weniger als 5% aller Szenarien
            würden Sie Geld verlieren. Das ist ein sehr gutes Risikoprofil.

            ✅ **Erwartete Rendite attraktiv** ({irr_mean:.1%}): Die durchschnittlich erwartete
            Rendite liegt über typischen Alternativanlagen.

            ✅ **Gutes Risiko-Rendite-Verhältnis** (Sharpe {sharpe:.2f}): Sie werden für das
            eingegangene Risiko angemessen entschädigt.

            **Fazit:** Dieses Investment bietet ein günstiges Verhältnis von Chance und Risiko.
            Selbst im schlechtesten realistischen Szenario (5%-Grenze) würden Sie
            noch {var_5:.1%} Rendite erzielen.
            """)
        elif prob_loss < 0.15 and irr_mean >= 0.04:
            st.info(f"""
            **Empfehlung: Solides Investment mit überschaubarem Risiko**

            ⚠️ **Moderates Verlustrisiko** ({prob_loss:.0%}): In {prob_loss:.0%} aller Szenarien
            könnten Sie Geld verlieren. Das ist im normalen Bereich für Immobilien.

            ✅ **Akzeptable Renditeerwartung** ({irr_mean:.1%}): Die erwartete Rendite liegt
            im marktüblichen Bereich.

            **Fazit:** Das Investment ist grundsätzlich tragfähig, bietet aber begrenzten
            Puffer gegen unvorhergesehene negative Entwicklungen. Prüfen Sie,
            ob Sie die möglichen Verluste im schlechtesten Fall ({var_5:.1%}) verkraften können.

            **Tipp:** Versuchen Sie, den Kaufpreis zu verhandeln oder die Finanzierungskonditionen
            zu verbessern, um das Risikoprofil zu optimieren.
            """)
        elif prob_loss < 0.30:
            st.warning(f"""
            **Empfehlung: Risikoreiches Investment - sorgfältig abwägen**

            ⚠️ **Erhöhtes Verlustrisiko** ({prob_loss:.0%}): In fast einem Drittel aller
            Szenarien würden Sie Geld verlieren. Das ist ein erhöhtes Risiko.

            ⚠️ **Begrenzte Renditeerwartung** ({irr_mean:.1%}): Die erwartete Rendite
            rechtfertigt das eingegangene Risiko nur begrenzt.

            **Fazit:** Dieses Investment sollte nur in Betracht gezogen werden, wenn:
            - Sie finanzielle Verluste gut verkraften können
            - Sie besondere Gründe haben (z.B. Eigennutzung geplant)
            - Keine besseren Alternativen verfügbar sind

            **Empfehlung:** Suchen Sie nach Möglichkeiten, den Kaufpreis zu senken,
            oder prüfen Sie alternative Objekte mit besserem Risiko-Rendite-Profil.
            """)
        else:
            st.error(f"""
            **Empfehlung: Von diesem Investment wird abgeraten**

            ❌ **Sehr hohes Verlustrisiko** ({prob_loss:.0%}): In mehr als einem Drittel
            aller Szenarien würden Sie Geld verlieren.

            ❌ **Unzureichende Renditeerwartung** ({irr_mean:.1%}): Die erwartete Rendite
            rechtfertigt das hohe Risiko nicht.

            ❌ **Schlechtes Risiko-Rendite-Verhältnis** (Sharpe {sharpe:.2f}): Sie werden
            für das eingegangene Risiko nicht angemessen entschädigt.

            **Fazit:** Dieses Investment hat ein ungünstiges Risikoprofil. Der Kaufpreis
            ist wahrscheinlich zu hoch für die erzielbaren Mieteinnahmen.

            **Dringende Empfehlung:** Verhandeln Sie einen deutlich niedrigeren Kaufpreis
            (mindestens 10-15% Rabatt) oder suchen Sie nach alternativen Objekten.
            """)


def render_data_explorer():
    """Render the Data Explorer tab."""
    st.header("Daten-Explorer")

    st.markdown("""
    Hier können Sie auf alle Rohdaten zugreifen und diese exportieren.
    Wählen Sie eine Datenquelle aus, um die verfügbaren Informationen anzuzeigen.
    """)

    # Data source selection
    data_source = st.selectbox(
        "Datenquelle auswählen",
        options=[
            "Marktdaten aller Städte",
            "Häuserpreisindex (historisch)",
            "Inflationsentwicklung",
            "Baugenehmigungen"
        ]
    )

    df = None  # Initialize df

    if data_source == "Marktdaten aller Städte":
        st.info(f"**{len(GERMAN_CITIES)} deutsche Städte** mit aktuellen Marktdaten verfügbar.")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox(
                "Sortieren nach",
                options=[
                    "Stadt (alphabetisch)",
                    "Kaufpreis pro Quadratmeter",
                    "Monatsmiete pro Quadratmeter",
                    "Bruttomietrendite",
                    "Einwohnerzahl"
                ]
            )
        with col2:
            filter_state = st.selectbox(
                "Nach Bundesland filtern",
                options=["Alle Bundesländer"] + sorted(list(set(c.state for c in GERMAN_CITIES.values())))
            )

        all_cities = market_data_fetcher.get_all_cities_data()
        data = []
        for key, city in all_cities.items():
            city_info = GERMAN_CITIES.get(key)
            if filter_state != "Alle Bundesländer" and city_info and city_info.state != filter_state:
                continue

            data.append({
                "Stadt": city.city_name,
                "Bundesland": city_info.state if city_info else "-",
                "Einwohner": f"{city_info.population:,}" if city_info else "-",
                "Kaufpreis pro Quadratmeter (Euro)": f"€{city.avg_price_sqm:,.0f}",
                "Monatsmiete pro Quadratmeter (Euro)": f"€{city.avg_rent_sqm:.2f}",
                "Bruttomietrendite": f"{city.gross_rental_yield:.2%}",
                "Preis-zu-Miete-Verhältnis (Jahre)": f"{city.price_to_rent_ratio:.1f}",
                "Preis-zu-Einkommen-Verhältnis": f"{city.price_to_income:.1f}",
                "Preisänderung zum Vorjahr": f"{city.price_yoy_change:+.1f}%",
                "Angebotsbestand (Monate)": f"{city.inventory_months:.1f}",
                "Arbeitslosenquote": f"{city.unemployment_rate:.1f}%"
            })

        df = pd.DataFrame(data)

        # Sort logic
        sort_map = {
            "Stadt (alphabetisch)": "Stadt",
            "Kaufpreis pro Quadratmeter": "Kaufpreis pro Quadratmeter (Euro)",
            "Monatsmiete pro Quadratmeter": "Monatsmiete pro Quadratmeter (Euro)",
            "Bruttomietrendite": "Bruttomietrendite",
            "Einwohnerzahl": "Einwohner"
        }

        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

        # Summary statistics
        st.markdown("#### Zusammenfassung")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Anzahl Städte", len(data))
        with col2:
            avg_prices = [float(d["Kaufpreis pro Quadratmeter (Euro)"].replace("€", "").replace(",", "")) for d in data]
            st.metric("Durchschnittlicher Kaufpreis", f"€{sum(avg_prices)/len(avg_prices):,.0f}/qm")
        with col3:
            avg_rents = [float(d["Monatsmiete pro Quadratmeter (Euro)"].replace("€", "")) for d in data]
            st.metric("Durchschnittliche Miete", f"€{sum(avg_rents)/len(avg_rents):.2f}/qm")
        with col4:
            avg_yields = [float(d["Bruttomietrendite"].replace("%", "")) for d in data]
            st.metric("Durchschnittliche Rendite", f"{sum(avg_yields)/len(avg_yields):.2f}%")

    elif data_source == "Häuserpreisindex (historisch)":
        st.markdown("""
        Der Häuserpreisindex zeigt die Entwicklung der Immobilienpreise in Deutschland
        über die Zeit. Der Index basiert auf dem Jahr 2015 als Referenzjahr (2015 = 100).
        """)
        hpi = destatis_fetcher.get_house_price_index()
        if not hpi.empty:
            hpi_df = hpi.reset_index()
            hpi_df.columns = ["Datum", "Preisindex (2015=100)"]
            st.dataframe(hpi_df, use_container_width=True, hide_index=True)
            df = hpi_df
        else:
            st.warning("Keine historischen Preisdaten verfügbar.")

    elif data_source == "Inflationsentwicklung":
        st.markdown("""
        Die Inflationsrate zeigt die jährliche Preissteigerung im Vergleich zum Vorjahr.
        Diese beeinflusst sowohl die Kreditkosten als auch die Mietentwicklung.
        """)
        cpi = destatis_fetcher.get_cpi()
        if not cpi.empty:
            inflation = cpi.pct_change(periods=12) * 100
            inflation_df = inflation.reset_index().dropna()
            inflation_df.columns = ["Datum", "Inflation (Prozent zum Vorjahr)"]
            st.dataframe(inflation_df, use_container_width=True, hide_index=True)
            df = inflation_df
        else:
            st.warning("Keine Inflationsdaten verfügbar.")

    elif data_source == "Baugenehmigungen":
        st.markdown("""
        Die Anzahl der Baugenehmigungen ist ein Frühindikator für das zukünftige Angebot
        an Wohnraum. Steigende Genehmigungen deuten auf mehr Neubau hin.
        """)
        permits = destatis_fetcher.get_building_permits()
        if not permits.empty:
            permits_df = permits.reset_index()
            permits_df.columns = ["Datum", "Anzahl Baugenehmigungen"]
            st.dataframe(permits_df, use_container_width=True, hide_index=True)
            df = permits_df
        else:
            st.warning("Keine Daten zu Baugenehmigungen verfügbar.")

    # Export button
    st.divider()
    if df is not None and not df.empty:
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="Daten als CSV-Datei exportieren",
            data=csv_data,
            file_name=f"immobilien_daten_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Wählen Sie eine Datenquelle aus, um Daten zu exportieren.")


def main():
    """Main dashboard function."""
    render_header()

    st.divider()

    # Main tabs - clear German labels without abbreviations
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Marktübersicht",
        "Regionale Analyse",
        "Investment-Rechner",
        "Zinsentwicklung",
        "Risiko-Simulation",
        "Daten-Explorer"
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
