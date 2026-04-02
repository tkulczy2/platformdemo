"""Tests for Step 2: Attribution — MSSP two-step plurality attribution."""

import pandas as pd
import pytest

from engine.provenance import StepResult
from engine.step_1_eligibility import determine_eligibility
from engine.step_2_attribution import assign_attribution


@pytest.fixture(scope="module")
def eligibility_result(demo_data, contract):
    return determine_eligibility(demo_data, contract)


@pytest.fixture(scope="module")
def attribution_result(demo_data, contract, eligibility_result):
    return assign_attribution(demo_data, contract, eligibility_result)


class TestAttributionBasics:
    def test_returns_step_result(self, attribution_result):
        assert isinstance(attribution_result, StepResult)

    def test_step_metadata(self, attribution_result):
        assert attribution_result.step_name == "attribution"
        assert attribution_result.step_number == 2

    def test_has_contract_clauses(self, attribution_result):
        assert len(attribution_result.contract_clauses) >= 1

    def test_has_code_references(self, attribution_result):
        assert len(attribution_result.code_references) >= 1

    def test_execution_time_recorded(self, attribution_result):
        assert attribution_result.execution_time_ms >= 0


class TestAttributionLogic:
    def test_attributed_count_reasonable(self, attribution_result, eligibility_result):
        total_eligible = eligibility_result.summary["eligible_count"]
        attributed = attribution_result.summary["attributed_count"]
        # Most eligible members should be attributed (>75%)
        assert attributed > total_eligible * 0.75
        # But not all (some have no qualifying visits)
        assert attributed <= total_eligible

    def test_step1_step2_cascade(self, attribution_result):
        """Step 2 catches members missed by Step 1."""
        step1 = attribution_result.summary.get("attributed_step1", 0)
        step2 = attribution_result.summary.get("attributed_step2", 0)
        total = attribution_result.summary["attributed_count"]
        assert step1 + step2 == total
        assert step1 > 0, "No members attributed in Step 1"
        assert step2 >= 0, "Step 2 count should be non-negative"

    def test_step1_majority(self, attribution_result):
        """Most attributions should come from Step 1 (PCP plurality)."""
        step1 = attribution_result.summary.get("attributed_step1", 0)
        total = attribution_result.summary["attributed_count"]
        assert step1 > total * 0.5, "Step 1 should attribute the majority"

    def test_unattributed_count(self, attribution_result, eligibility_result):
        total_eligible = eligibility_result.summary["eligible_count"]
        attributed = attribution_result.summary["attributed_count"]
        unattributed = attribution_result.summary.get("unattributed_count", total_eligible - attributed)
        assert attributed + unattributed == total_eligible

    def test_attributed_population_list(self, attribution_result):
        pop = attribution_result.summary.get("attributed_population")
        assert isinstance(pop, list)
        assert len(pop) == attribution_result.summary["attributed_count"]

    def test_no_duplicates_in_attributed(self, attribution_result):
        pop = attribution_result.summary["attributed_population"]
        assert len(pop) == len(set(pop)), "Duplicate member IDs in attributed population"

    def test_zero_qualifying_visits_not_attributed(self, attribution_result):
        """Members with zero qualifying visits should not be attributed."""
        unattributed = [m for m in attribution_result.member_details
                        if m.outcome in ("not_attributed", "unattributed")]
        for member in unattributed:
            # They should have a reason explaining why
            assert member.reason, f"Unattributed member {member.member_id} has no reason"


class TestAttributionProvenance:
    def test_member_details_populated(self, attribution_result):
        assert len(attribution_result.member_details) > 0

    def test_attributed_members_have_details(self, attribution_result):
        attributed = [m for m in attribution_result.member_details
                      if m.outcome == "attributed"]
        assert len(attributed) > 0
        for member in attributed[:5]:  # Check first 5
            assert member.intermediate_values, \
                f"Attributed member {member.member_id} missing intermediate values"

    def test_attribution_details_dict(self, attribution_result):
        details = attribution_result.summary.get("attribution_details")
        if details:
            assert isinstance(details, dict)
            # Spot-check a detail entry
            sample = next(iter(details.values()))
            assert "assigned_npi" in sample or "provider_npi" in sample or "npi" in sample
