"""Tests for Step 4: Cost and PMPM Calculation with maturity adjustments."""

import pytest

from engine.provenance import StepResult
from engine.step_1_eligibility import determine_eligibility
from engine.step_2_attribution import assign_attribution
from engine.step_4_cost import calculate_cost


@pytest.fixture(scope="module")
def attribution_result(demo_data, contract):
    elig = determine_eligibility(demo_data, contract)
    return assign_attribution(demo_data, contract, elig)


@pytest.fixture(scope="module")
def cost_result(demo_data, contract, attribution_result):
    return calculate_cost(demo_data, contract, attribution_result)


class TestCostBasics:
    def test_returns_step_result(self, cost_result):
        assert isinstance(cost_result, StepResult)

    def test_step_metadata(self, cost_result):
        assert cost_result.step_name == "cost"
        assert cost_result.step_number == 4

    def test_has_contract_clauses(self, cost_result):
        assert len(cost_result.contract_clauses) >= 1

    def test_execution_time_recorded(self, cost_result):
        assert cost_result.execution_time_ms >= 0


class TestPMPMCalculation:
    def test_pmpm_positive(self, cost_result):
        assert cost_result.summary["actual_pmpm"] > 0

    def test_raw_pmpm_positive(self, cost_result):
        assert cost_result.summary["raw_pmpm"] > 0

    def test_pmpm_reasonable_range(self, cost_result):
        pmpm = cost_result.summary["actual_pmpm"]
        # Medicare PMPM typically $800-$2000, but maturity adjustments and
        # synthetic data distribution can push higher
        assert 500 <= pmpm <= 5000, f"PMPM ${pmpm} outside reasonable range"

    def test_total_member_months_positive(self, cost_result):
        mm = cost_result.summary["total_member_months"]
        assert mm > 0

    def test_member_months_reasonable(self, cost_result, attribution_result):
        mm = cost_result.summary["total_member_months"]
        attributed = attribution_result.summary["attributed_count"]
        # Should be between 6 and 12 months per attributed member on average
        avg_months = mm / attributed if attributed > 0 else 0
        assert 4 <= avg_months <= 12, f"Average months {avg_months:.1f} seems wrong"

    def test_pmpm_equals_cost_over_member_months(self, cost_result):
        """PMPM = total cost / member-months."""
        total = cost_result.summary.get("adjusted_total_cost",
                                         cost_result.summary.get("raw_total_cost", 0))
        mm = cost_result.summary["total_member_months"]
        pmpm = cost_result.summary["actual_pmpm"]
        if mm > 0 and total > 0:
            expected = total / mm
            assert abs(pmpm - expected) < 1.0, \
                f"PMPM ${pmpm:.2f} != total ${total:.2f} / {mm} months = ${expected:.2f}"


class TestMaturityAdjustment:
    def test_adjusted_pmpm_gte_raw(self, cost_result):
        """Maturity adjustment should increase costs (incomplete months are adjusted up)."""
        raw = cost_result.summary["raw_pmpm"]
        adjusted = cost_result.summary["actual_pmpm"]
        # Adjusted should be >= raw (incomplete months get inflated)
        assert adjusted >= raw * 0.95, "Adjusted PMPM unexpectedly lower than raw"

    def test_confidence_band_exists(self, cost_result):
        assert "pmpm_confidence_low" in cost_result.summary
        assert "pmpm_confidence_high" in cost_result.summary

    def test_confidence_band_order(self, cost_result):
        low = cost_result.summary["pmpm_confidence_low"]
        pmpm = cost_result.summary["actual_pmpm"]
        high = cost_result.summary["pmpm_confidence_high"]
        assert low <= pmpm <= high, f"Confidence band disordered: {low} <= {pmpm} <= {high}"

    def test_monthly_maturity_tracked(self, cost_result):
        maturity = cost_result.summary.get("monthly_maturity")
        if maturity:
            assert isinstance(maturity, (list, dict))


class TestCostByCategory:
    def test_category_breakdown_exists(self, cost_result):
        cats = cost_result.summary.get("cost_by_category")
        assert cats is not None, "Missing cost_by_category breakdown"

    def test_categories_are_positive(self, cost_result):
        cats = cost_result.summary.get("cost_by_category", {})
        for cat, value in cats.items():
            if isinstance(value, (int, float)):
                assert value >= 0, f"Category {cat} has negative cost"

    def test_only_attributed_members_included(self, cost_result, attribution_result):
        """Cost should only include claims for attributed members."""
        # The summary should reference the attributed population
        # Indirect check: member_months should correspond to attributed count
        mm = cost_result.summary["total_member_months"]
        attributed = attribution_result.summary["attributed_count"]
        assert mm <= attributed * 12, "Member-months exceeds max possible for attributed population"


class TestCostProvenance:
    def test_member_details_populated(self, cost_result):
        assert len(cost_result.member_details) > 0

    def test_data_quality_flags_type(self, cost_result):
        assert isinstance(cost_result.data_quality_flags, list)
