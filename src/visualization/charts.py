"""
Chart Factory for German Real Estate Investment Analysis Dashboard.

Creates professional Plotly visualizations with dark text for readability.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Professional color scheme with BLACK text for readability
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#2ca02c",
    "warning": "#ff7f0e",
    "danger": "#d62728",
    "neutral": "#7f7f7f",
    "light_blue": "#aec7e8",
    "light_green": "#98df8a",
    "light_orange": "#ffbb78",
    "background": "#ffffff",
    "text": "#000000",  # BLACK for maximum readability
    "text_secondary": "#333333",
}

STATUS_COLORS = {
    "green": "#28a745",
    "yellow": "#ffc107",
    "red": "#dc3545",
}

# Standard layout for all charts - BLACK text everywhere
STANDARD_LAYOUT = {
    "font": {"family": "Arial, sans-serif", "color": "#000000", "size": 12},
    "title_font": {"color": "#000000", "size": 16},
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
}


class ChartFactory:
    """Factory for creating professional charts with readable dark text."""

    @staticmethod
    def _apply_dark_text(fig: go.Figure) -> go.Figure:
        """Apply dark text styling to all chart elements."""
        fig.update_layout(
            font=dict(color="#000000", family="Arial, sans-serif"),
            title_font=dict(color="#000000"),
            legend_font=dict(color="#000000"),
        )
        fig.update_xaxes(
            title_font=dict(color="#000000"),
            tickfont=dict(color="#000000"),
            gridcolor='#cccccc'
        )
        fig.update_yaxes(
            title_font=dict(color="#000000"),
            tickfont=dict(color="#000000"),
            gridcolor='#cccccc'
        )
        return fig

    @staticmethod
    def create_crash_gauge(
        score: float,
        recommendation: str,
        title: str = "Crash-Wahrscheinlichkeit"
    ) -> go.Figure:
        """Create a speedometer-style gauge for crash probability."""
        if score < 30:
            bar_color = STATUS_COLORS["green"]
        elif score < 60:
            bar_color = STATUS_COLORS["yellow"]
        else:
            bar_color = STATUS_COLORS["red"]

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 48, "color": "#000000"}},
            title={
                "text": f"<b>{title}</b><br><span style='font-size:16px;color:#000000'>{recommendation}</span>",
                "font": {"color": "#000000", "size": 18}
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 2,
                    "tickcolor": "#000000",
                    "tickfont": {"color": "#000000", "size": 12}
                },
                "bar": {"color": bar_color, "thickness": 0.8},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#000000",
                "steps": [
                    {"range": [0, 20], "color": "#c8e6c9"},
                    {"range": [20, 40], "color": "#dcedc8"},
                    {"range": [40, 60], "color": "#fff9c4"},
                    {"range": [60, 80], "color": "#ffccbc"},
                    {"range": [80, 100], "color": "#ffcdd2"}
                ],
                "threshold": {
                    "line": {"color": "#000000", "width": 4},
                    "thickness": 0.8,
                    "value": score
                }
            }
        ))

        fig.update_layout(
            height=320,
            margin=dict(l=30, r=30, t=80, b=30),
            paper_bgcolor="white",
            font=dict(color="#000000")
        )

        return fig

    @staticmethod
    def create_category_breakdown(
        categories: List[Dict[str, Any]],
        title: str = "Score-Aufschlüsselung nach Kategorie"
    ) -> go.Figure:
        """Create a horizontal bar chart showing category contributions."""
        names = [c["name"] for c in categories]
        weighted = [c["weighted_score"] for c in categories]
        colors = [STATUS_COLORS.get(c["status"], COLORS["neutral"]) for c in categories]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=names,
            x=weighted,
            orientation='h',
            marker_color=colors,
            text=[f"{s:.1f}" for s in weighted],
            textposition='outside',
            textfont=dict(color="#000000", size=12),
            name='Gewichteter Beitrag'
        ))

        fig.update_layout(
            title=dict(text=title, font=dict(color="#000000", size=16)),
            xaxis_title="Beitrag zum Gesamtscore",
            yaxis={"categoryorder": "total ascending"},
            height=320,
            margin=dict(l=180, r=60, t=60, b=50),
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_price_chart(
        data: pd.DataFrame,
        title: str = "Preisentwicklung",
        y_column: str = "value"
    ) -> go.Figure:
        """Create a time series chart for prices."""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[y_column],
            mode='lines',
            name='Preis pro Quadratmeter',
            line=dict(color=COLORS["primary"], width=2.5),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.15)'
        ))

        fig.update_layout(
            title=dict(text=title, font=dict(color="#000000", size=16)),
            xaxis_title="Datum",
            yaxis_title="Euro pro Quadratmeter",
            height=400,
            margin=dict(l=80, r=30, t=60, b=50),
            paper_bgcolor="white",
            plot_bgcolor="white",
            hovermode='x unified'
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_rate_forecast_chart(
        forecasts: pd.DataFrame,
        current_rate: float,
        title: str = "Zinsprognose"
    ) -> go.Figure:
        """Create a fan chart for interest rate forecasts."""
        fig = go.Figure()

        # 95% confidence band
        fig.add_trace(go.Scatter(
            x=list(forecasts['date']) + list(forecasts['date'][::-1]),
            y=list(forecasts['upper_95']) + list(forecasts['lower_95'][::-1]),
            fill='toself',
            fillcolor='rgba(31, 119, 180, 0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            name='95% Konfidenzintervall',
            showlegend=True
        ))

        # 66% confidence band
        fig.add_trace(go.Scatter(
            x=list(forecasts['date']) + list(forecasts['date'][::-1]),
            y=list(forecasts['upper_66']) + list(forecasts['lower_66'][::-1]),
            fill='toself',
            fillcolor='rgba(31, 119, 180, 0.25)',
            line=dict(color='rgba(255,255,255,0)'),
            name='66% Konfidenzintervall',
            showlegend=True
        ))

        # Point forecast
        fig.add_trace(go.Scatter(
            x=forecasts['date'],
            y=forecasts['forecast'],
            mode='lines',
            name='Prognose',
            line=dict(color=COLORS["primary"], width=3)
        ))

        # Current rate marker
        fig.add_hline(
            y=current_rate,
            line_dash="dash",
            line_color=COLORS["danger"],
            line_width=2,
            annotation_text=f"Aktueller Zinssatz: {current_rate:.2f}%",
            annotation_font=dict(color="#000000", size=12)
        )

        fig.update_layout(
            title=dict(text=title, font=dict(color="#000000", size=16)),
            xaxis_title="Datum",
            yaxis_title="Zinssatz in Prozent",
            height=420,
            margin=dict(l=80, r=30, t=60, b=50),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#000000")
            )
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_tornado_chart(
        sensitivity: Dict[str, Dict[str, float]],
        title: str = "Sensitivitätsanalyse - Interne Rendite"
    ) -> go.Figure:
        """Create a tornado chart for sensitivity analysis."""
        base_irr = list(sensitivity.values())[0].get("base_irr", 0)

        # Full German labels
        label_mapping = {
            "purchase_price": "Kaufpreis",
            "interest_rate": "Zinssatz",
            "initial_rent": "Anfangsmiete",
            "vacancy_rate": "Leerstandsquote",
            "exit_growth": "Wertsteigerung beim Verkauf",
        }

        low_impacts = []
        high_impacts = []
        labels = []

        for var, data in sensitivity.items():
            low_delta = (data["low_irr"] - base_irr) * 100
            high_delta = (data["high_irr"] - base_irr) * 100
            low_impacts.append(low_delta)
            high_impacts.append(high_delta)
            labels.append(label_mapping.get(var, var.replace("_", " ").title()))

        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=labels,
            x=low_impacts,
            orientation='h',
            name='Pessimistisches Szenario',
            marker_color=COLORS["danger"],
            textfont=dict(color="#000000")
        ))

        fig.add_trace(go.Bar(
            y=labels,
            x=high_impacts,
            orientation='h',
            name='Optimistisches Szenario',
            marker_color=COLORS["secondary"],
            textfont=dict(color="#000000")
        ))

        fig.add_vline(x=0, line_width=2, line_color="#000000")

        fig.update_layout(
            title=dict(
                text=f"{title}<br><span style='font-size:12px;color:#333333'>Basis-Rendite: {base_irr:.1%}</span>",
                font=dict(color="#000000", size=16)
            ),
            xaxis_title="Veränderung der Rendite (Prozentpunkte)",
            yaxis={"categoryorder": "total ascending"},
            barmode='overlay',
            height=420,
            margin=dict(l=200, r=40, t=100, b=60),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#000000")
            )
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_monte_carlo_histogram(
        irr_distribution: np.ndarray,
        var_5: float,
        mean_irr: float,
        title: str = "Renditeverteilung aus Monte-Carlo-Simulation"
    ) -> go.Figure:
        """Create histogram of Monte Carlo IRR distribution."""
        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=irr_distribution * 100,
            nbinsx=50,
            name='Renditeverteilung',
            marker_color=COLORS["primary"],
            opacity=0.8
        ))

        # VaR line
        fig.add_vline(
            x=var_5 * 100,
            line_dash="dash",
            line_color=COLORS["danger"],
            line_width=2,
            annotation_text=f"Risikokennzahl (5. Perzentil): {var_5:.1%}",
            annotation_font=dict(color="#000000", size=11),
            annotation_position="top"
        )

        # Mean line
        fig.add_vline(
            x=mean_irr * 100,
            line_dash="solid",
            line_color=COLORS["secondary"],
            line_width=2,
            annotation_text=f"Erwartete Rendite: {mean_irr:.1%}",
            annotation_font=dict(color="#000000", size=11),
            annotation_position="top"
        )

        fig.update_layout(
            title=dict(text=title, font=dict(color="#000000", size=16)),
            xaxis_title="Interne Rendite in Prozent",
            yaxis_title="Anzahl Simulationen",
            height=420,
            margin=dict(l=80, r=30, t=60, b=50),
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_cashflow_waterfall(
        cash_flows: List[Dict[str, Any]],
        title: str = "Jährliche Cashflow-Entwicklung nach Steuern"
    ) -> go.Figure:
        """Create a bar chart showing cash flow by year."""
        years = [f"Jahr {cf['year']}" for cf in cash_flows[:10]]
        values = [cf['after_tax_cash_flow'] for cf in cash_flows[:10]]
        colors = [COLORS["secondary"] if v >= 0 else COLORS["danger"] for v in values]

        fig = go.Figure(go.Bar(
            x=years,
            y=values,
            marker_color=colors,
            text=[f"€{v:,.0f}" for v in values],
            textposition='outside',
            textfont=dict(color="#000000", size=11)
        ))

        fig.add_hline(y=0, line_width=2, line_color="#000000")

        fig.update_layout(
            title=dict(text=title, font=dict(color="#000000", size=16)),
            xaxis_title="Jahr",
            yaxis_title="Cashflow in Euro",
            height=420,
            margin=dict(l=80, r=30, t=60, b=50),
            paper_bgcolor="white",
            plot_bgcolor="white"
        )

        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_city_comparison_chart(
        data: pd.DataFrame,
        metric: str = "Preis pro Quadratmeter (Euro)",
        title: str = "Städtevergleich"
    ) -> go.Figure:
        """Create a bar chart comparing cities on a metric."""
        # Map column names to full German
        column_mapping = {
            "Preis/qm": "Preis pro Quadratmeter (Euro)",
            "Miete/qm": "Monatsmiete pro Quadratmeter (Euro)",
            "Arbeitslosigkeit": "Arbeitslosenquote in Prozent"
        }

        display_metric = column_mapping.get(metric, metric)
        actual_column = metric if metric in data.columns else [k for k, v in column_mapping.items() if v == metric][0] if any(v == metric for v in column_mapping.values()) else metric

        fig = go.Figure(go.Bar(
            x=data["Stadt"],
            y=data[actual_column] if actual_column in data.columns else data[metric],
            marker_color=COLORS["primary"],
            text=data[actual_column] if actual_column in data.columns else data[metric],
            textposition='outside',
            textfont=dict(color="#000000", size=11)
        ))

        fig.update_layout(
            title=dict(text=f"{title}: {display_metric}", font=dict(color="#000000", size=16)),
            xaxis_title="Stadt",
            yaxis_title=display_metric,
            height=420,
            margin=dict(l=80, r=30, t=60, b=120),
            paper_bgcolor="white",
            plot_bgcolor="white"
        )

        fig.update_xaxes(tickangle=45)
        fig = ChartFactory._apply_dark_text(fig)
        return fig

    @staticmethod
    def create_metrics_cards(metrics: Dict[str, Any]) -> go.Figure:
        """Create a figure with key metric indicators."""
        n_metrics = len(metrics)
        cols = min(4, n_metrics)
        rows = (n_metrics + cols - 1) // cols

        fig = make_subplots(
            rows=rows,
            cols=cols,
            specs=[[{"type": "indicator"}] * cols for _ in range(rows)],
            horizontal_spacing=0.1,
            vertical_spacing=0.15
        )

        for i, (name, value) in enumerate(metrics.items()):
            row = i // cols + 1
            col = i % cols + 1

            if isinstance(value, float) and abs(value) < 1:
                display_value = value * 100
                number_format = {"suffix": "%", "valueformat": ".1f"}
            elif isinstance(value, float):
                display_value = value
                number_format = {"prefix": "€", "valueformat": ",.0f"}
            else:
                display_value = value
                number_format = {}

            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=display_value,
                    title={"text": name, "font": {"color": "#000000", "size": 14}},
                    number={**number_format, "font": {"color": "#000000", "size": 24}}
                ),
                row=row,
                col=col
            )

        fig.update_layout(
            height=160 * rows,
            margin=dict(l=30, r=30, t=30, b=30),
            paper_bgcolor="white"
        )

        return fig


chart_factory = ChartFactory()
