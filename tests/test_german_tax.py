"""
Tests for German Real Estate Tax Calculator.

Tests coverage:
- Grunderwerbsteuer rates by Bundesland
- AfA depreciation rates by building year
- Acquisition cost calculations
- Capital gains tax with Spekulationsfrist
- Kirchensteuer and Solidaritätszuschlag
"""

import pytest
from datetime import datetime

from src.utils.german_tax import (
    GRUNDERWERBSTEUER_RATES,
    get_grunderwerbsteuer_rate,
    get_kirchensteuer_rate,
    get_depreciation_rate,
    calculate_acquisition_costs,
    calculate_depreciation_schedule,
    calculate_capital_gains_tax,
    calculate_rental_income_tax,
    get_all_bundeslaender,
    AcquisitionCosts,
    DepreciationSchedule,
    CapitalGainsTax
)


class TestGrunderwerbsteuer:
    """Tests for Grunderwerbsteuer (property transfer tax) rates."""

    def test_all_bundeslaender_have_rates(self):
        """Verify all 16 Bundesländer have defined rates."""
        assert len(GRUNDERWERBSTEUER_RATES) == 16

    def test_rate_ranges(self):
        """Verify rates are within legal German range (3.5% - 6.5%)."""
        for bundesland, rate in GRUNDERWERBSTEUER_RATES.items():
            assert 0.035 <= rate <= 0.065, f"{bundesland} rate {rate} out of range"

    def test_specific_bundeslaender_rates(self):
        """Test known Grunderwerbsteuer rates."""
        # Bayern has the lowest rate
        assert get_grunderwerbsteuer_rate("Bayern") == 0.035
        # Brandenburg, NRW, Saarland, SH, Thüringen have highest
        assert get_grunderwerbsteuer_rate("Brandenburg") == 0.065
        assert get_grunderwerbsteuer_rate("Nordrhein-Westfalen") == 0.065
        assert get_grunderwerbsteuer_rate("Schleswig-Holstein") == 0.065
        # Berlin
        assert get_grunderwerbsteuer_rate("Berlin") == 0.06
        # Baden-Württemberg
        assert get_grunderwerbsteuer_rate("Baden-Württemberg") == 0.05

    def test_unknown_bundesland_default(self):
        """Unknown Bundesland should return default rate (5%)."""
        assert get_grunderwerbsteuer_rate("Fantasieland") == 0.05


class TestKirchensteuer:
    """Tests for Kirchensteuer rates."""

    def test_bayern_bw_rate(self):
        """Bayern and BW have 8% Kirchensteuer."""
        assert get_kirchensteuer_rate("Bayern") == 0.08
        assert get_kirchensteuer_rate("Baden-Württemberg") == 0.08

    def test_other_laender_rate(self):
        """All other Bundesländer have 9% Kirchensteuer."""
        for bundesland in ["Berlin", "Hamburg", "Hessen", "Nordrhein-Westfalen"]:
            assert get_kirchensteuer_rate(bundesland) == 0.09


class TestDepreciationRates:
    """Tests for AfA (depreciation) rates based on construction year."""

    def test_pre_1925_buildings(self):
        """Buildings before 1925: 2.5% over 40 years."""
        rate, years, description = get_depreciation_rate(1900)
        assert rate == 0.025
        assert years == 40
        assert "2,5%" in description
        assert "vor 1925" in description

    def test_1925_2022_buildings(self):
        """Buildings 1925-2022: 2% over 50 years."""
        rate, years, description = get_depreciation_rate(1980)
        assert rate == 0.02
        assert years == 50

        rate, years, description = get_depreciation_rate(2022)
        assert rate == 0.02
        assert years == 50

    def test_2023_plus_buildings(self):
        """Buildings 2023+: 3% over ~33 years (JStG 2022)."""
        rate, years, description = get_depreciation_rate(2023)
        assert rate == 0.03
        assert years == 34  # Approximately 33.33 years
        assert "JStG 2022" in description

        rate, years, description = get_depreciation_rate(2025)
        assert rate == 0.03

    def test_boundary_years(self):
        """Test boundary years between rate changes."""
        # Year 1924 should be pre-1925 rate
        rate, _, _ = get_depreciation_rate(1924)
        assert rate == 0.025

        # Year 1925 should be standard rate
        rate, _, _ = get_depreciation_rate(1925)
        assert rate == 0.02


class TestAcquisitionCosts:
    """Tests for total acquisition cost calculations."""

    def test_basic_acquisition_costs(self):
        """Test acquisition cost calculation with standard assumptions."""
        result = calculate_acquisition_costs(
            purchase_price=500000,
            bundesland="Bayern",
            include_makler=True
        )

        assert isinstance(result, AcquisitionCosts)
        assert result.purchase_price == 500000

        # Bayern: 3.5% Grunderwerbsteuer
        assert result.grunderwerbsteuer == 500000 * 0.035
        assert result.grunderwerbsteuer_rate == 0.035

        # Notar: ~1.5%
        assert result.notar_fees == 500000 * 0.015

        # Grundbuch: ~0.5%
        assert result.grundbuch_fees == 500000 * 0.005

        # Makler: 3.57%
        assert result.makler_fees == 500000 * 0.0357

        # Total should be sum of all
        expected_total = 500000 + result.grunderwerbsteuer + result.notar_fees + \
                        result.grundbuch_fees + result.makler_fees
        assert result.total_acquisition_cost == expected_total

    def test_without_makler(self):
        """Test acquisition costs without broker fees."""
        result = calculate_acquisition_costs(
            purchase_price=500000,
            bundesland="Bayern",
            include_makler=False
        )
        assert result.makler_fees == 0

    def test_highest_tax_bundesland(self):
        """Test with highest Grunderwerbsteuer rate (NRW)."""
        result = calculate_acquisition_costs(
            purchase_price=500000,
            bundesland="Nordrhein-Westfalen",
            include_makler=True
        )
        assert result.grunderwerbsteuer_rate == 0.065
        assert result.grunderwerbsteuer == 500000 * 0.065

    def test_acquisition_percentage(self):
        """Test that acquisition percentage is correctly calculated."""
        result = calculate_acquisition_costs(
            purchase_price=100000,
            bundesland="Bayern",
            include_makler=True
        )
        # (total - purchase) / purchase should equal percentage
        calculated_pct = (result.total_acquisition_cost - result.purchase_price) / result.purchase_price
        assert abs(result.acquisition_cost_percentage - calculated_pct) < 0.0001


class TestDepreciationSchedule:
    """Tests for depreciation schedule calculations."""

    def test_new_building_depreciation(self):
        """Test depreciation for new building (2023+)."""
        result = calculate_depreciation_schedule(
            purchase_price=500000,
            baujahr=2024,
            land_value_ratio=0.20
        )

        assert isinstance(result, DepreciationSchedule)
        # Depreciable base should be 80% of purchase price
        assert result.depreciable_base == 400000
        # 3% annual rate for new buildings
        assert result.annual_rate == 0.03
        # Annual amount
        assert result.annual_amount == 400000 * 0.03

    def test_old_building_depreciation(self):
        """Test depreciation for old building (pre-1925)."""
        result = calculate_depreciation_schedule(
            purchase_price=300000,
            baujahr=1920,
            land_value_ratio=0.25
        )

        # 2.5% for pre-1925
        assert result.annual_rate == 0.025
        assert result.depreciable_base == 300000 * 0.75

    def test_land_value_excluded(self):
        """Verify land value is excluded from depreciation base."""
        result = calculate_depreciation_schedule(
            purchase_price=1000000,
            baujahr=2000,
            land_value_ratio=0.30
        )
        # 70% of value is building, 30% is land
        assert result.depreciable_base == 700000


class TestCapitalGainsTax:
    """Tests for capital gains tax with Spekulationsfrist."""

    def test_tax_free_after_10_years(self):
        """Holdings >= 10 years should be tax-exempt."""
        result = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=40000,
            holding_period_years=10,
            marginal_tax_rate=0.42
        )

        assert isinstance(result, CapitalGainsTax)
        assert result.is_tax_exempt is True
        assert result.taxable_gain == 0
        assert result.estimated_tax == 0

    def test_taxable_before_10_years(self):
        """Holdings < 10 years should be taxable."""
        result = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=40000,
            holding_period_years=8,
            marginal_tax_rate=0.42
        )

        assert result.is_tax_exempt is False
        # Gain = 600000 - (500000 - 40000) = 140000
        assert result.capital_gain == 140000
        assert result.taxable_gain == 140000
        assert result.estimated_tax > 0

    def test_no_gain_no_tax(self):
        """No capital gain should result in no tax."""
        result = calculate_capital_gains_tax(
            sale_price=450000,
            original_cost_basis=500000,
            accumulated_depreciation=0,
            holding_period_years=5,
            marginal_tax_rate=0.42
        )

        # Loss, not gain
        assert result.capital_gain == -50000
        assert result.estimated_tax == 0

    def test_depreciation_recapture(self):
        """Accumulated depreciation should reduce cost basis."""
        # Without depreciation
        result1 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=0,
            holding_period_years=5,
            marginal_tax_rate=0.42
        )

        # With depreciation
        result2 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=50000,
            holding_period_years=5,
            marginal_tax_rate=0.42
        )

        # Higher depreciation = higher taxable gain
        assert result2.capital_gain > result1.capital_gain

    def test_soli_and_kirchen(self):
        """Test Solidaritätszuschlag and Kirchensteuer inclusion."""
        # Without church tax
        result1 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=400000,
            accumulated_depreciation=0,
            holding_period_years=5,
            marginal_tax_rate=0.42,
            bundesland="Bayern",
            is_church_member=False
        )

        # With church tax
        result2 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=400000,
            accumulated_depreciation=0,
            holding_period_years=5,
            marginal_tax_rate=0.42,
            bundesland="Bayern",
            is_church_member=True
        )

        # Church member pays more
        assert result2.estimated_tax > result1.estimated_tax

    def test_spekulationsfrist_boundary(self):
        """Test the exact 10-year boundary."""
        # Exactly 9 years - taxable
        result9 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=0,
            holding_period_years=9,
            marginal_tax_rate=0.42
        )
        assert result9.is_tax_exempt is False

        # Exactly 10 years - tax-free
        result10 = calculate_capital_gains_tax(
            sale_price=600000,
            original_cost_basis=500000,
            accumulated_depreciation=0,
            holding_period_years=10,
            marginal_tax_rate=0.42
        )
        assert result10.is_tax_exempt is True


class TestRentalIncomeTax:
    """Tests for rental income tax calculations."""

    def test_positive_taxable_income(self):
        """Test with positive taxable income."""
        result = calculate_rental_income_tax(
            annual_rent=24000,
            annual_depreciation=8000,
            annual_interest=6000,
            annual_operating_costs=2000,
            marginal_tax_rate=0.42
        )

        # Taxable = 24000 - 8000 - 6000 - 2000 = 8000
        assert result["taxable_income"] == 8000
        assert result["is_loss"] is False
        assert result["total_tax"] > 0

    def test_rental_loss(self):
        """Test with rental loss (can offset other income)."""
        result = calculate_rental_income_tax(
            annual_rent=12000,
            annual_depreciation=10000,
            annual_interest=8000,
            annual_operating_costs=2000,
            marginal_tax_rate=0.42
        )

        # Taxable = 12000 - 10000 - 8000 - 2000 = -8000
        assert result["taxable_income"] == -8000
        assert result["is_loss"] is True
        assert result["tax_savings"] > 0


class TestUtilities:
    """Tests for utility functions."""

    def test_get_all_bundeslaender(self):
        """Test list of all Bundesländer."""
        laender = get_all_bundeslaender()
        assert len(laender) == 16
        assert laender == sorted(laender)  # Sorted
        assert "Bayern" in laender
        assert "Berlin" in laender


# Run with: pytest tests/test_german_tax.py -v
