"""
Chart Factory for German Real Estate Investment Analysis Dashboard.

Creates professional Plotly visualizations for:
- Crash probability gauges
- Price and rate charts
- Sensitivity tornado charts
- Monte Carlo distributions
- Cash flow waterfalls
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Professional color scheme (Goldman Sachs / BlackRock style)
COLORS = {
    "primary": "#1f77b4",      # Professional blue
    "secondary": "#2ca02c",    # Green
    "warning": "#ff7f0e",      # Orange
    "danger": "#d62728",       # Red
    "neutral": "#7f7f7f",      # Gray
    "light_blue": "#aec7e8",
    "light_green": "#98df8a",
    "light_orange": "#ffbb78",
    "background": "#f8f9fa",
    "text": "#2c3e50",
}

# Traffic light colors
STATUS_COLORS = {
    "green": "#28a745",
    "yellow": "#ffc107",
    "red": "#dc3545",
}


class ChartFactory:
    """Factory for creating professional charts."""

    @staticmethod
    def create_crash_gauge(
        score: float,
        recommendation: str,
        title: str = "Crash-Wahrscheinlichkeit"
    ) -> go.Figure:
        """
        Create a speedometer-style gauge for crash probability.

        Args:
            score: Crash probability score (0-100)
            recommendation: Text recommendation (e.g., "HOLD", "BUY")
            title: Chart title

        Returns:
            Plotly figure
        """
        # Determine color based on score
        if score < 30:
            bar_color = STATUS_COLORS["green"]
        elif score < 60:
            bar_color = STATUS_COLORS["yellow"]
        else:
            bar_color = STATUS_COLORS["red"]

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            number={"suffix": "%", "font": {"size": 40}},
            title={"text": f"<b>{title}</b><br><span style='font-size:14px'>{recommendation}</span>"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": COLORS["text"]},
                "bar": {"color": bar_color},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": COLORS["text"],
                "steps": [
                    {"range": [0, 20], "color": "#d4edda"},
                    {"range": [20, 40], "color": "#c3e6cb"},
                    {"range": [40, 60], "color": "#fff3cd"},
                    {"range": [60, 80], "color": "#f8d7da"},
                    {"range": [80, 100], "color": "#f5c6cb"}
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": score
                }
            }
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=60, b=20),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
        )

        return fig

    @staticmethod
    def create_category_breakdown(
        categories: List[Dict[str, Any]],
        title: str = "Score-Breakdown nach Kategorie"
    ) -> go.Figure:
        """
        Create a horizontal bar chart showing category contributions.

        Args:
            categories: List of dicts with 'name', 'score', 'weight', 'status'
            title: Chart title

        Returns:
            Plotly figure
        """
        names = [c["name"] for c in categories]
        scores = [c["score"] for c in categories]
        weighted = [c["weighted_score"] for c in categories]
        colors = [STATUS_COLORS.get(c["status"], COLORS["neutral"]) for c in categories]

        fig = go.Figure()

        # Add bars for weighted contribution
        fig.add_trace(go.Bar(
            y=names,
            x=weighted,
            orientation='h',
            marker_color=colors,
            text=[f"{s:.1f}" for s in weighted],
            textposition='auto',
            name='Gewichteter Beitrag'
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Beitrag zum Gesamtscore",
            yaxis={"categoryorder": "total ascending"},
            height=300,
            margin=dict(l=150, r=20, t=50, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False
        )

        fig.update_xaxes(gridcolor='lightgray', gridwidth=1)

        return fig

    @staticmethod
    def create_price_chart(
        data: pd.DataFrame,
        title: str = "Preisentwicklung",
        y_column: str = "value"
    ) -> go.Figure:
        """
        Create a time series chart for prices.

        Args:
            data: DataFrame with datetime index and value column
            title: Chart title
            y_column: Column name for y-axis

        Returns:
            Plotly figure
        """
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[y_column],
            mode='lines',
            name='Preis/qm',
            line=dict(color=COLORS["primary"], width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Datum",
            yaxis_title="EUR/qm",
            height=400,
            margin=dict(l=60, r=20, t=50, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white",
            hovermode='x unified'
        )

        fig.update_xaxes(gridcolor='lightgray', gridwidth=1)
        fig.update_yaxes(gridcolor='lightgray', gridwidth=1)

        return fig

    @staticmethod
    def create_rate_forecast_chart(
        forecasts: pd.DataFrame,
        current_rate: float,
        title: str = "Zinsprognose"
    ) -> go.Figure:
        """
        Create a fan chart for interest rate forecasts.

        Args:
            forecasts: DataFrame with columns: date, forecast, lower_66, upper_66, lower_95, upper_95
            current_rate: Current interest rate
            title: Chart title

        Returns:
            Plotly figure
        """
        fig = go.Figure()

        # 95% confidence band
        fig.add_trace(go.Scatter(
            x=list(forecasts['date']) + list(forecasts['date'][::-1]),
            y=list(forecasts['upper_95']) + list(forecasts['lower_95'][::-1]),
            fill='toself',
            fillcolor='rgba(31, 119, 180, 0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            name='95% Konfidenz',
            showlegend=True
        ))

        # 66% confidence band
        fig.add_trace(go.Scatter(
            x=list(forecasts['date']) + list(forecasts['date'][::-1]),
            y=list(forecasts['upper_66']) + list(forecasts['lower_66'][::-1]),
            fill='toself',
            fillcolor='rgba(31, 119, 180, 0.3)',
            line=dict(color='rgba(255,255,255,0)'),
            name='66% Konfidenz',
            showlegend=True
        ))

        # Point forecast
        fig.add_trace(go.Scatter(
            x=forecasts['date'],
            y=forecasts['forecast'],
            mode='lines',
            name='Prognose',
            line=dict(color=COLORS["primary"], width=2)
        ))

        # Current rate marker
        fig.add_hline(
            y=current_rate,
            line_dash="dash",
            line_color=COLORS["danger"],
            annotation_text=f"Aktuell: {current_rate:.2f}%"
        )

        fig.update_layout(
            title=title,
            xaxis_title="Datum",
            yaxis_title="Zinssatz (%)",
            height=400,
            margin=dict(l=60, r=20, t=50, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(gridcolor='lightgray')
        fig.update_yaxes(gridcolor='lightgray')

        return fig

    @staticmethod
    def create_tornado_chart(
        sensitivity: Dict[str, Dict[str, float]],
        title: str = "Sensitivitätsanalyse (IRR)"
    ) -> go.Figure:
        """
        Create a tornado chart for sensitivity analysis.

        Args:
            sensitivity: Dict with variable names and low/high IRR impacts
            title: Chart title

        Returns:
            Plotly figure
        """
        variables = list(sensitivity.keys())
        base_irr = list(sensitivity.values())[0].get("base_irr", 0)

        low_impacts = []
        high_impacts = []
        labels = []

        for var, data in sensitivity.items():
            low_delta = (data["low_irr"] - base_irr) * 100  # Convert to percentage points
            high_delta = (data["high_irr"] - base_irr) * 100
            low_impacts.append(low_delta)
            high_impacts.append(high_delta)
            labels.append(var.replace("_", " ").title())

        fig = go.Figure()

        # Low impact bars
        fig.add_trace(go.Bar(
            y=labels,
            x=low_impacts,
            orientation='h',
            name='Unteres Szenario',
            marker_color=COLORS["danger"]
        ))

        # High impact bars
        fig.add_trace(go.Bar(
            y=labels,
            x=high_impacts,
            orientation='h',
            name='Oberes Szenario',
            marker_color=COLORS["secondary"]
        ))

        # Add vertical line at base IRR (0)
        fig.add_vline(x=0, line_width=2, line_dash="solid", line_color="black")

        fig.update_layout(
            title=f"{title}<br><sup>Basis-IRR: {base_irr:.1%}</sup>",
            xaxis_title="Veränderung IRR (Prozentpunkte)",
            yaxis={"categoryorder": "total ascending"},
            barmode='overlay',
            height=400,
            margin=dict(l=150, r=20, t=80, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(gridcolor='lightgray', zeroline=True, zerolinewidth=2)

        return fig

    @staticmethod
    def create_monte_carlo_histogram(
        irr_distribution: np.ndarray,
        var_5: float,
        mean_irr: float,
        title: str = "IRR Verteilung (Monte Carlo)"
    ) -> go.Figure:
        """
        Create histogram of Monte Carlo IRR distribution.

        Args:
            irr_distribution: Array of IRR values
            var_5: 5th percentile (Value at Risk)
            mean_irr: Mean IRR
            title: Chart title

        Returns:
            Plotly figure
        """
        fig = go.Figure()

        # Histogram
        fig.add_trace(go.Histogram(
            x=irr_distribution * 100,  # Convert to percentage
            nbinsx=50,
            name='IRR Verteilung',
            marker_color=COLORS["primary"],
            opacity=0.7
        ))

        # VaR line
        fig.add_vline(
            x=var_5 * 100,
            line_dash="dash",
            line_color=COLORS["danger"],
            annotation_text=f"VaR (5%): {var_5:.1%}"
        )

        # Mean line
        fig.add_vline(
            x=mean_irr * 100,
            line_dash="solid",
            line_color=COLORS["secondary"],
            annotation_text=f"Mittelwert: {mean_irr:.1%}"
        )

        fig.update_layout(
            title=title,
            xaxis_title="IRR (%)",
            yaxis_title="Häufigkeit",
            height=400,
            margin=dict(l=60, r=20, t=50, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False
        )

        fig.update_xaxes(gridcolor='lightgray')
        fig.update_yaxes(gridcolor='lightgray')

        return fig

    @staticmethod
    def create_cashflow_waterfall(
        cash_flows: List[Dict[str, Any]],
        title: str = "Cash Flow Entwicklung"
    ) -> go.Figure:
        """
        Create a waterfall chart showing cash flow components.

        Args:
            cash_flows: List of cash flow dictionaries by year
            title: Chart title

        Returns:
            Plotly figure
        """
        # Use a subset of years for clarity
        years = [f"Jahr {cf['year']}" for cf in cash_flows[:10]]
        values = [cf['after_tax_cash_flow'] for cf in cash_flows[:10]]

        # Color based on positive/negative
        colors = [COLORS["secondary"] if v >= 0 else COLORS["danger"] for v in values]

        fig = go.Figure(go.Bar(
            x=years,
            y=values,
            marker_color=colors,
            text=[f"€{v:,.0f}" for v in values],
            textposition='outside'
        ))

        fig.add_hline(y=0, line_width=1, line_color="black")

        fig.update_layout(
            title=title,
            xaxis_title="Jahr",
            yaxis_title="Cash Flow (EUR)",
            height=400,
            margin=dict(l=60, r=20, t=50, b=40),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white"
        )

        fig.update_xaxes(gridcolor='lightgray')
        fig.update_yaxes(gridcolor='lightgray')

        return fig

    @staticmethod
    def create_city_comparison_chart(
        data: pd.DataFrame,
        metric: str = "Preis/qm",
        title: str = "Städtevergleich"
    ) -> go.Figure:
        """
        Create a bar chart comparing cities on a metric.

        Args:
            data: DataFrame with city comparison data
            metric: Column name for the metric to compare
            title: Chart title

        Returns:
            Plotly figure
        """
        fig = go.Figure(go.Bar(
            x=data["Stadt"],
            y=data[metric],
            marker_color=COLORS["primary"],
            text=data[metric],
            textposition='outside'
        ))

        fig.update_layout(
            title=f"{title}: {metric}",
            xaxis_title="Stadt",
            yaxis_title=metric,
            height=400,
            margin=dict(l=60, r=20, t=50, b=100),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white",
            plot_bgcolor="white"
        )

        fig.update_xaxes(tickangle=45, gridcolor='lightgray')
        fig.update_yaxes(gridcolor='lightgray')

        return fig

    @staticmethod
    def create_metrics_cards(
        metrics: Dict[str, Any]
    ) -> go.Figure:
        """
        Create a figure with key metric indicators.

        Args:
            metrics: Dictionary of metric name -> value

        Returns:
            Plotly figure with indicator cards
        """
        n_metrics = len(metrics)
        cols = min(4, n_metrics)
        rows = (n_metrics + cols - 1) // cols

        fig = make_subplots(
            rows=rows,
            cols=cols,
            specs=[[{"type": "indicator"}] * cols for _ in range(rows)],
            horizontal_spacing=0.1,
            vertical_spacing=0.1
        )

        for i, (name, value) in enumerate(metrics.items()):
            row = i // cols + 1
            col = i % cols + 1

            if isinstance(value, float) and value < 1:
                number_format = {"suffix": "%", "valueformat": ".1%"}
            elif isinstance(value, float):
                number_format = {"prefix": "€", "valueformat": ",.0f"}
            else:
                number_format = {}

            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=value * 100 if isinstance(value, float) and value < 1 else value,
                    title={"text": name},
                    number=number_format
                ),
                row=row,
                col=col
            )

        fig.update_layout(
            height=150 * rows,
            margin=dict(l=20, r=20, t=20, b=20),
            font={"family": "Roboto, sans-serif"},
            paper_bgcolor="white"
        )

        return fig


# Singleton instance
chart_factory = ChartFactory()
