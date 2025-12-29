"""
Monte Carlo Simulation for German Real Estate Investment Analysis.

Runs stochastic simulations to understand the distribution of possible
outcomes and risk metrics for property investments.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from datetime import datetime
import logging

from .dcf_model import DCFModel, PropertyInput, Scenario

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationParameters:
    """Parameters for Monte Carlo simulation."""
    n_simulations: int = 10000

    # Interest rate parameters (Vasicek model)
    rate_mean_reversion: float = 0.15  # Speed of mean reversion
    rate_long_term_mean: float = 0.035  # Long-term average rate
    rate_volatility: float = 0.01  # Annual volatility

    # House price parameters
    price_drift: float = 0.02  # Expected annual growth
    price_volatility: float = 0.08  # Annual volatility

    # Rent parameters
    rent_drift: float = 0.02
    rent_volatility: float = 0.03

    # Vacancy parameters
    vacancy_mean: float = 0.03
    vacancy_volatility: float = 0.02

    # Correlation matrix
    correlation_rate_price: float = -0.3  # Higher rates = lower prices
    correlation_price_rent: float = 0.5   # Prices and rents move together


@dataclass
class SimulationResult:
    """Result of Monte Carlo simulation."""
    n_simulations: int
    irr_distribution: np.ndarray
    npv_distribution: np.ndarray
    equity_multiple_distribution: np.ndarray

    # Summary statistics
    irr_mean: float
    irr_std: float
    irr_median: float
    irr_percentiles: Dict[int, float]

    npv_mean: float
    npv_percentiles: Dict[int, float]

    # Risk metrics
    probability_of_loss: float
    value_at_risk_5: float  # 5th percentile IRR
    conditional_var_5: float  # Average of worst 5%
    sharpe_ratio: float

    # Distribution data for plotting
    irr_histogram: Tuple[np.ndarray, np.ndarray]


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for real estate investments.

    Uses stochastic models for:
    - Interest rates (Vasicek/CIR model)
    - House prices (Geometric Brownian Motion)
    - Rental income (correlated GBM)
    - Vacancy rates (mean-reverting)
    """

    def __init__(self, params: Optional[SimulationParameters] = None):
        """
        Initialize simulator.

        Args:
            params: Simulation parameters
        """
        self.params = params or SimulationParameters()
        self.dcf_model = DCFModel()
        self._rng = np.random.default_rng()

    def run_simulation(
        self,
        base_inputs: PropertyInput,
        n_simulations: Optional[int] = None
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation on a property investment.

        Args:
            base_inputs: Base case property inputs
            n_simulations: Number of simulations (overrides params if set)

        Returns:
            SimulationResult with distribution of outcomes
        """
        n_sims = n_simulations or self.params.n_simulations
        holding_years = base_inputs.holding_period_years

        logger.info(f"Running {n_sims} Monte Carlo simulations...")

        # Generate correlated random paths
        paths = self._generate_correlated_paths(n_sims, holding_years)

        irr_results = []
        npv_results = []
        em_results = []

        for i in range(n_sims):
            # Apply stochastic adjustments
            sim_inputs = self._apply_simulation_path(
                base_inputs,
                paths["rate"][i],
                paths["price"][i],
                paths["rent"][i],
                paths["vacancy"][i]
            )

            # Calculate returns for this simulation
            try:
                result = self.dcf_model._calculate_scenario(sim_inputs, Scenario.BASE)
                irr_results.append(result.metrics.irr_after_tax)
                npv_results.append(result.metrics.npv)
                em_results.append(result.metrics.equity_multiple)
            except Exception:
                # Skip failed simulations
                continue

        # Convert to numpy arrays
        irr_array = np.array(irr_results)
        npv_array = np.array(npv_results)
        em_array = np.array(em_results)

        # Calculate statistics
        percentiles = [5, 10, 25, 50, 75, 90, 95]

        irr_pcts = {p: np.percentile(irr_array, p) for p in percentiles}
        npv_pcts = {p: np.percentile(npv_array, p) for p in percentiles}

        # Risk metrics
        prob_loss = np.mean(irr_array < 0)
        var_5 = np.percentile(irr_array, 5)
        cvar_5 = np.mean(irr_array[irr_array <= var_5])

        # Sharpe ratio (assuming risk-free rate of 3%)
        risk_free = 0.03
        sharpe = (np.mean(irr_array) - risk_free) / np.std(irr_array) if np.std(irr_array) > 0 else 0

        # Histogram data
        hist, bin_edges = np.histogram(irr_array, bins=50)

        return SimulationResult(
            n_simulations=len(irr_results),
            irr_distribution=irr_array,
            npv_distribution=npv_array,
            equity_multiple_distribution=em_array,
            irr_mean=np.mean(irr_array),
            irr_std=np.std(irr_array),
            irr_median=np.median(irr_array),
            irr_percentiles=irr_pcts,
            npv_mean=np.mean(npv_array),
            npv_percentiles=npv_pcts,
            probability_of_loss=prob_loss,
            value_at_risk_5=var_5,
            conditional_var_5=cvar_5,
            sharpe_ratio=sharpe,
            irr_histogram=(hist, bin_edges)
        )

    def _generate_correlated_paths(
        self,
        n_sims: int,
        n_years: int
    ) -> Dict[str, np.ndarray]:
        """
        Generate correlated random paths for simulation variables.

        Uses Cholesky decomposition for correlation.
        """
        p = self.params

        # Correlation matrix
        corr_matrix = np.array([
            [1.0, p.correlation_rate_price, 0.0, 0.0],
            [p.correlation_rate_price, 1.0, p.correlation_price_rent, 0.0],
            [0.0, p.correlation_price_rent, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])

        # Cholesky decomposition
        L = np.linalg.cholesky(corr_matrix)

        # Generate uncorrelated random numbers
        Z = self._rng.standard_normal((n_sims, n_years, 4))

        # Apply correlation
        corr_Z = np.einsum('ijk,lk->ijl', Z, L)

        # Generate paths
        paths = {}

        # Interest rate path (Vasicek model)
        rate_path = np.zeros((n_sims, n_years))
        rate_path[:, 0] = p.rate_long_term_mean

        for t in range(1, n_years):
            rate_path[:, t] = (
                rate_path[:, t-1] +
                p.rate_mean_reversion * (p.rate_long_term_mean - rate_path[:, t-1]) +
                p.rate_volatility * corr_Z[:, t, 0]
            )
            rate_path[:, t] = np.maximum(0.005, rate_path[:, t])  # Floor at 0.5%

        paths["rate"] = rate_path

        # Price path (GBM cumulative growth)
        price_returns = (
            p.price_drift - 0.5 * p.price_volatility**2 +
            p.price_volatility * corr_Z[:, :, 1]
        )
        paths["price"] = np.exp(np.cumsum(price_returns, axis=1))

        # Rent path (GBM cumulative growth)
        rent_returns = (
            p.rent_drift - 0.5 * p.rent_volatility**2 +
            p.rent_volatility * corr_Z[:, :, 2]
        )
        paths["rent"] = np.exp(np.cumsum(rent_returns, axis=1))

        # Vacancy path (mean-reverting)
        vacancy_path = np.zeros((n_sims, n_years))
        vacancy_path[:, 0] = p.vacancy_mean

        for t in range(1, n_years):
            vacancy_path[:, t] = (
                vacancy_path[:, t-1] +
                0.5 * (p.vacancy_mean - vacancy_path[:, t-1]) +
                p.vacancy_volatility * corr_Z[:, t, 3]
            )
            vacancy_path[:, t] = np.clip(vacancy_path[:, t], 0, 0.30)

        paths["vacancy"] = vacancy_path

        return paths

    def _apply_simulation_path(
        self,
        base_inputs: PropertyInput,
        rate_path: np.ndarray,
        price_path: np.ndarray,
        rent_path: np.ndarray,
        vacancy_path: np.ndarray
    ) -> PropertyInput:
        """
        Apply simulation path to create stochastic inputs.

        We average the paths to get overall adjustments.
        """
        import copy
        sim_inputs = copy.deepcopy(base_inputs)

        # Use average rate over holding period
        avg_rate = np.mean(rate_path)
        sim_inputs.interest_rate = avg_rate

        # Exit price growth based on final price level
        final_price_level = price_path[-1]
        implied_growth = (final_price_level ** (1 / len(price_path))) - 1
        sim_inputs.exit_price_growth = implied_growth

        # Rent growth based on rent path
        final_rent_level = rent_path[-1]
        implied_rent_growth = (final_rent_level ** (1 / len(rent_path))) - 1
        sim_inputs.rent_growth_rate = implied_rent_growth

        # Average vacancy
        sim_inputs.vacancy_rate = np.mean(vacancy_path)

        return sim_inputs

    def generate_report(self, result: SimulationResult) -> str:
        """Generate a text report from simulation results."""
        report = f"""
## Monte Carlo Simulation Report

**Simulations Run:** {result.n_simulations:,}

### IRR Distribution

| Metric | Value |
|--------|-------|
| Mean | {result.irr_mean:.2%} |
| Std Dev | {result.irr_std:.2%} |
| Median | {result.irr_median:.2%} |
| 5th Percentile | {result.irr_percentiles[5]:.2%} |
| 25th Percentile | {result.irr_percentiles[25]:.2%} |
| 75th Percentile | {result.irr_percentiles[75]:.2%} |
| 95th Percentile | {result.irr_percentiles[95]:.2%} |

### Risk Metrics

| Metric | Value |
|--------|-------|
| Probability of Loss | {result.probability_of_loss:.1%} |
| Value at Risk (5%) | {result.value_at_risk_5:.2%} |
| Conditional VaR (5%) | {result.conditional_var_5:.2%} |
| Sharpe Ratio | {result.sharpe_ratio:.2f} |

### NPV Distribution

| Percentile | NPV |
|------------|-----|
| 5th | €{result.npv_percentiles[5]:,.0f} |
| 25th | €{result.npv_percentiles[25]:,.0f} |
| 50th | €{result.npv_percentiles[50]:,.0f} |
| 75th | €{result.npv_percentiles[75]:,.0f} |
| 95th | €{result.npv_percentiles[95]:,.0f} |

### Interpretation

"""
        if result.probability_of_loss < 0.05:
            report += "- **Low Risk:** Less than 5% probability of negative return\n"
        elif result.probability_of_loss < 0.15:
            report += "- **Moderate Risk:** 5-15% probability of negative return\n"
        else:
            report += "- **High Risk:** More than 15% probability of negative return\n"

        if result.sharpe_ratio > 1:
            report += "- **Attractive Risk-Adjusted Return:** Sharpe ratio above 1\n"
        elif result.sharpe_ratio > 0.5:
            report += "- **Acceptable Risk-Adjusted Return:** Sharpe ratio between 0.5-1\n"
        else:
            report += "- **Poor Risk-Adjusted Return:** Sharpe ratio below 0.5\n"

        return report


# Singleton instance
monte_carlo_simulator = MonteCarloSimulator()
