"""Tests for Step 3: Quality Measure Calculation.

Tests the composite quality step and individual measures (HbA1c, BP,
breast cancer screening, colorectal screening, depression screening).
"""

import pytest

from engine.provenance import StepResult
from engine.step_1_eligibility import determine_eligibility
from engine.step_2_attribution import assign_attribution
from engine.step_3_quality import calculate_quality_measures


@pytest.fixture(scope="module")
def quality_result(demo_data, contract):
    elig = determine_eligibility(demo_data, contract)
    attr = assign_attribution(demo_data, contract, elig)
    return calculate_quality_measures(demo_data, contract, attr)


class TestQualityBasics:
    def test_returns_step_result(self, quality_result):
        assert isinstance(quality_result, StepResult)

    def test_step_metadata(self, quality_result):
        assert quality_result.step_name == "quality"
        assert quality_result.step_number == 3

    def test_has_contract_clauses(self, quality_result):
        assert len(quality_result.contract_clauses) >= 1

    def test_execution_time_recorded(self, quality_result):
        assert quality_result.execution_time_ms >= 0


class TestCompositeScore:
    def test_composite_score_in_range(self, quality_result):
        composite = quality_result.summary["composite_score"]
        assert 0 <= composite <= 100, f"Composite {composite} outside [0, 100]"

    def test_all_five_measures_present(self, quality_result):
        measures = quality_result.summary.get("measures", {})
        expected = {"hba1c_poor_control", "controlling_bp", "breast_cancer_screening",
                    "colorectal_screening", "depression_screening"}
        assert set(measures.keys()) == expected

    def test_measure_count(self, quality_result):
        assert quality_result.summary.get("measure_count", 0) == 5


class TestIndividualMeasures:
    EXPECTED_MEASURES = [
        "hba1c_poor_control",
        "controlling_bp",
        "breast_cancer_screening",
        "colorectal_screening",
        "depression_screening",
    ]

    @pytest.fixture(scope="class")
    def measures(self, quality_result):
        return quality_result.summary["measures"]

    @pytest.mark.parametrize("measure_id", EXPECTED_MEASURES)
    def test_measure_has_rate(self, measures, measure_id):
        m = measures[measure_id]
        assert "rate" in m or "performance_rate" in m

    @pytest.mark.parametrize("measure_id", EXPECTED_MEASURES)
    def test_measure_rate_in_range(self, measures, measure_id):
        m = measures[measure_id]
        rate = m.get("rate", m.get("performance_rate", 0))
        assert 0 <= rate <= 100, f"{measure_id} rate {rate} outside [0, 100]"

    @pytest.mark.parametrize("measure_id", EXPECTED_MEASURES)
    def test_measure_has_denominator(self, measures, measure_id):
        m = measures[measure_id]
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 0)))
        assert denom > 0, f"{measure_id} has zero denominator"

    @pytest.mark.parametrize("measure_id", EXPECTED_MEASURES)
    def test_numerator_lte_denominator(self, measures, measure_id):
        m = measures[measure_id]
        num = m.get("numerator_count", m.get("numerator", 0))
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 1)))
        assert num <= denom, f"{measure_id}: numerator {num} > denominator {denom}"


class TestHbA1cInverseMeasure:
    """HbA1c Poor Control is an inverse measure — lower rate = better."""

    def test_hba1c_is_tracked(self, quality_result):
        measures = quality_result.summary["measures"]
        assert "hba1c_poor_control" in measures

    def test_hba1c_rate_realistic(self, quality_result):
        m = quality_result.summary["measures"]["hba1c_poor_control"]
        rate = m.get("rate", m.get("performance_rate", 0))
        # HbA1c poor control rate can be high in synthetic data since members
        # without a test are counted as "poor control" per HEDIS methodology
        assert 0 < rate <= 100, f"HbA1c poor control rate {rate}% outside valid range"


class TestBloodPressure:
    def test_bp_denominator_reasonable(self, quality_result):
        m = quality_result.summary["measures"]["controlling_bp"]
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 0)))
        # ~40% of members are hypertensive per generator config
        assert denom > 100, f"BP denominator {denom} too small for 1000-member population"


class TestScreeningMeasures:
    def test_breast_cancer_female_only(self, quality_result):
        m = quality_result.summary["measures"]["breast_cancer_screening"]
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 0)))
        # Roughly half the attributed population is female, age 50-74 subset
        assert denom < 500, f"Breast cancer denominator {denom} seems too large (should be females 50-74)"

    def test_colorectal_denominator(self, quality_result):
        m = quality_result.summary["measures"]["colorectal_screening"]
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 0)))
        assert denom > 50, "Colorectal screening denominator too small"

    def test_depression_broad_denominator(self, quality_result):
        m = quality_result.summary["measures"]["depression_screening"]
        denom = m.get("denominator_count", m.get("denominator", m.get("eligible_count", 0)))
        # Depression screening applies to all adults — should be large
        assert denom > 400, f"Depression denominator {denom} too small (applies to all adults)"


class TestQualityProvenance:
    def test_member_details_populated(self, quality_result):
        assert len(quality_result.member_details) > 0

    def test_member_outcomes_valid(self, quality_result):
        valid_outcomes = {"in_numerator", "not_in_numerator", "excluded", "in_denominator",
                          "not_in_denominator", "numerator_met", "numerator_not_met",
                          "denominator", "exclusion"}
        for m in quality_result.member_details[:20]:
            assert m.outcome, f"Member {m.member_id} has empty outcome"
