"""
Tests for NPV (Net Present Value) calculation.

The correct NPV formula is:
    NPV = CF₀ + Σ(CFₜ / (1+r)^t) for t=1 to n

CRITICAL: Period 0 is NOT discounted (it represents today's value).
This is different from numpy_financial.npv() which discounts ALL periods.
"""

import pytest
import math

from src.utils.helpers import calculate_npv


class TestNPVBasics:
    """Basic NPV calculation tests."""

    def test_single_period(self):
        """Test with single cash flow at period 0."""
        # Only period 0, no discounting
        result = calculate_npv([-100000], 0.08)
        assert result == -100000

    def test_zero_discount_rate(self):
        """With 0% discount rate, NPV = sum of all cash flows."""
        cash_flows = [-100000, 30000, 30000, 30000, 30000]
        result = calculate_npv(cash_flows, 0)
        expected = sum(cash_flows)
        assert result == expected

    def test_empty_cash_flows(self):
        """Empty cash flow list should return 0."""
        result = calculate_npv([], 0.08)
        assert result == 0.0


class TestNPVPeriodZeroNotDiscounted:
    """Critical tests verifying period 0 is NOT discounted."""

    def test_period_0_not_discounted(self):
        """Period 0 should NOT be discounted."""
        # Only period 0 investment
        investment = -100000
        result = calculate_npv([investment], 0.10)
        # Should equal exactly the investment, not discounted
        assert result == investment

    def test_period_0_vs_period_1(self):
        """Compare period 0 vs period 1 treatment."""
        discount_rate = 0.10

        # $10,000 at period 0
        npv_period_0 = calculate_npv([10000], discount_rate)
        assert npv_period_0 == 10000  # Not discounted

        # $10,000 at period 1 (after initial 0)
        npv_period_1 = calculate_npv([0, 10000], discount_rate)
        expected = 10000 / (1 + discount_rate)  # = 9090.91
        assert abs(npv_period_1 - expected) < 0.01

    def test_manual_calculation(self):
        """Verify NPV matches manual calculation."""
        cash_flows = [-100000, 30000, 40000, 50000]
        discount_rate = 0.08

        # Manual calculation:
        # Period 0: -100000 (NOT discounted)
        # Period 1: 30000 / 1.08 = 27777.78
        # Period 2: 40000 / 1.08² = 34293.55
        # Period 3: 50000 / 1.08³ = 39691.61
        # Total: -100000 + 27777.78 + 34293.55 + 39691.61 = 1762.94

        expected_p0 = -100000
        expected_p1 = 30000 / (1.08 ** 1)
        expected_p2 = 40000 / (1.08 ** 2)
        expected_p3 = 50000 / (1.08 ** 3)
        expected_npv = expected_p0 + expected_p1 + expected_p2 + expected_p3

        result = calculate_npv(cash_flows, discount_rate)
        assert abs(result - expected_npv) < 0.01


class TestNPVTypicalInvestments:
    """Test with typical real estate investment scenarios."""

    def test_positive_npv_investment(self):
        """Test investment with positive NPV (good investment)."""
        # Initial investment, then positive cash flows
        cash_flows = [-200000, 25000, 26000, 27000, 28000, 29000, 30000, 31000, 32000, 33000, 234000]
        result = calculate_npv(cash_flows, 0.08)
        # Should be positive for a good investment
        assert result > 0

    def test_negative_npv_investment(self):
        """Test investment with negative NPV (bad investment)."""
        # High initial cost, low returns
        cash_flows = [-500000, 20000, 20000, 20000, 20000, 20000]
        result = calculate_npv(cash_flows, 0.08)
        # Should be negative
        assert result < 0

    def test_break_even_npv(self):
        """Test investment near break-even."""
        # At IRR, NPV should be approximately 0
        cash_flows = [-100000, 20000, 20000, 20000, 20000, 20000, 20000]
        # This has an IRR of about 5.47%
        result_at_irr = calculate_npv(cash_flows, 0.0547)
        assert abs(result_at_irr) < 500  # Close to zero

    def test_terminal_value_included(self):
        """Test with terminal value (property sale at end)."""
        # 10 years of cash flows plus terminal sale
        cash_flows = [-300000]  # Initial investment
        for year in range(1, 11):
            cash_flows.append(18000)  # Annual cash flow
        cash_flows[-1] += 400000  # Add terminal value to last year

        result = calculate_npv(cash_flows, 0.08)
        # With high discount rate, even terminal value may not offset initial investment
        # This is actually a marginal investment at 8% discount
        assert result > 0  # Should still be positive


class TestNPVDiscountRates:
    """Test NPV sensitivity to discount rates."""

    def test_higher_rate_lower_npv(self):
        """Higher discount rate should result in lower NPV."""
        cash_flows = [-100000, 30000, 30000, 30000, 30000, 30000]

        npv_5pct = calculate_npv(cash_flows, 0.05)
        npv_10pct = calculate_npv(cash_flows, 0.10)
        npv_15pct = calculate_npv(cash_flows, 0.15)

        assert npv_5pct > npv_10pct > npv_15pct

    def test_high_discount_rate(self):
        """Test with very high discount rate."""
        cash_flows = [-100000, 50000, 50000, 50000]
        result = calculate_npv(cash_flows, 0.50)
        # Even with 50% discount rate, should calculate correctly
        expected = -100000 + 50000/1.5 + 50000/2.25 + 50000/3.375
        assert abs(result - expected) < 0.01


class TestNPVEdgeCases:
    """Edge case tests."""

    def test_all_zeros(self):
        """All zero cash flows."""
        result = calculate_npv([0, 0, 0, 0], 0.08)
        assert result == 0

    def test_large_numbers(self):
        """Test with large numbers (millions)."""
        cash_flows = [-10000000, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000]
        result = calculate_npv(cash_flows, 0.08)
        # Should handle large numbers without overflow
        # NPV is negative because 6 years of 2M doesn't cover 10M at 8% discount
        # But calculation should work correctly
        assert isinstance(result, float)
        # Verify calculation is reasonable
        assert result > -2000000  # Not extremely negative

    def test_many_periods(self):
        """Test with many periods (30 years)."""
        cash_flows = [-500000]
        for _ in range(30):
            cash_flows.append(30000)
        cash_flows[-1] += 600000  # Terminal value

        result = calculate_npv(cash_flows, 0.08)
        # Should calculate correctly for long periods
        assert isinstance(result, float)

    def test_negative_cash_flows_middle(self):
        """Test with negative cash flows in middle (renovation years)."""
        cash_flows = [-100000, 15000, 15000, -20000, 20000, 20000, 120000]
        result = calculate_npv(cash_flows, 0.08)
        # Should handle negative cash flows in any position
        assert isinstance(result, float)


class TestNPVCorrectFormula:
    """
    Test that our NPV implementation uses the correct financial formula.

    Correct NPV formula: CF₀ + Σ(CFₜ / (1+r)^t) for t=1 to n
    Period 0 is NOT discounted (it represents today's value).
    """

    def test_matches_textbook_formula(self):
        """Verify our NPV matches the standard textbook formula."""
        cash_flows = [-100000, 30000, 40000, 50000]
        discount_rate = 0.08

        our_result = calculate_npv(cash_flows, discount_rate)

        # Standard NPV formula: CF[0] + sum(CF[t] / (1+r)^t)
        expected = (-100000 + 30000/1.08 + 40000/(1.08**2) +
                   50000/(1.08**3))

        # Verify our result matches the expected formula
        assert abs(our_result - expected) < 0.01

    def test_period_zero_not_discounted(self):
        """Verify period 0 cash flow is not discounted."""
        # If we invest $100,000 today, NPV of just that should be -$100,000
        result = calculate_npv([-100000], 0.10)
        assert result == -100000  # Not discounted at all

    def test_consistent_with_irr_at_zero_npv(self):
        """At IRR, NPV should be approximately zero."""
        cash_flows = [-100000, 50000, 50000, 50000]
        # IRR of this is about 23.4%
        from src.utils.helpers import calculate_irr
        irr = calculate_irr(cash_flows)

        npv_at_irr = calculate_npv(cash_flows, irr)
        assert abs(npv_at_irr) < 1  # Should be very close to zero


# Run with: pytest tests/test_npv.py -v
