"""Tests for the brief engine — transforms pipeline output into clinical briefs."""

import json
from pathlib import Path

import pytest

from engine.brief_engine import BriefEngine, PatientBrief

SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"
CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "contracts"


@pytest.fixture(scope="module")
def schedule():
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def brief_engine(pipeline_result, schedule):
    contract = json.load(open(CONTRACTS_DIR / "sample_mssp_contract.json"))
    return BriefEngine(pipeline_result, contract, schedule)


@pytest.fixture(scope="module")
def all_briefs(brief_engine):
    return brief_engine.generate_all_briefs()


class TestBriefGeneration:
    def test_generates_brief_for_every_appointment(self, all_briefs, schedule):
        total_apts = sum(len(d["appointments"]) for d in schedule["days"])
        assert len(all_briefs) == total_apts

    def test_brief_is_patient_brief(self, all_briefs):
        for brief in all_briefs:
            assert isinstance(brief, PatientBrief)

    def test_priority_actions_max_three(self, all_briefs):
        for brief in all_briefs:
            assert len(brief.priority_actions) <= 3

    def test_attribution_risk_has_valid_status(self, all_briefs):
        valid = {"stable", "moderate_risk", "high_risk", "new_attribution"}
        for brief in all_briefs:
            assert brief.attribution_risk.status in valid

    def test_quality_gaps_sorted_by_priority(self, all_briefs):
        for brief in all_briefs:
            if len(brief.quality_gaps) > 1:
                scores = [g.priority_score for g in brief.quality_gaps]
                assert scores == sorted(scores, reverse=True)


class TestCrossoverPatient:
    def test_crossover_patient_exists(self, all_briefs):
        crossover = [b for b in all_briefs if b.is_crossover_patient]
        assert len(crossover) == 1

    def test_crossover_has_discrepancy_detail(self, all_briefs):
        crossover = [b for b in all_briefs if b.is_crossover_patient][0]
        assert crossover.crossover_discrepancy is not None


class TestClinicalLanguage:
    """Brief text must use clinical language, not analytics jargon."""

    FORBIDDEN_TERMS = [
        "HEDIS", "PMPM", "numerator", "denominator",
    ]

    def test_priority_actions_use_clinical_language(self, all_briefs):
        for brief in all_briefs:
            for action in brief.priority_actions:
                text = f"{action.action_text} {action.reason_text}".lower()
                for term in self.FORBIDDEN_TERMS:
                    assert term.lower() not in text, (
                        f"Forbidden term '{term}' found in brief {brief.appointment_id}: {text}"
                    )

    def test_gap_descriptions_use_clinical_language(self, all_briefs):
        for brief in all_briefs:
            for gap in brief.quality_gaps:
                text = f"{gap.measure_name} {gap.action_needed}".lower()
                for term in self.FORBIDDEN_TERMS:
                    assert term.lower() not in text, (
                        f"Forbidden term '{term}' found in gap: {text}"
                    )
