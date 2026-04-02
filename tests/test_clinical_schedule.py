"""Tests for the clinical schedule generator."""

import json
from pathlib import Path

import pandas as pd
import pytest

SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"
MEMBERS_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "members.csv"


@pytest.fixture(scope="module")
def schedule():
    """Load the generated weekly schedule."""
    if not SCHEDULE_PATH.exists():
        pytest.skip("weekly_schedule.json not generated yet")
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def member_ids():
    """Load all valid member IDs."""
    return set(pd.read_csv(MEMBERS_PATH)["member_id"])


class TestScheduleStructure:
    def test_has_five_days(self, schedule):
        assert len(schedule["days"]) == 5

    def test_days_are_monday_to_friday(self, schedule):
        expected = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        actual = [d["day_name"] for d in schedule["days"]]
        assert actual == expected

    def test_appointment_count_range(self, schedule):
        total = sum(len(d["appointments"]) for d in schedule["days"])
        assert 45 <= total <= 55, f"Expected 45-55 appointments, got {total}"

    def test_has_practice_metadata(self, schedule):
        week = schedule["schedule_week"]
        assert "practice_name" in week
        assert len(week["providers"]) == 3

    def test_providers_have_npi(self, schedule):
        for p in schedule["schedule_week"]["providers"]:
            assert "npi" in p
            assert "name" in p


class TestScheduleMembers:
    def test_all_member_ids_valid(self, schedule, member_ids):
        for day in schedule["days"]:
            for apt in day["appointments"]:
                assert apt["member_id"] in member_ids, f"Invalid member_id: {apt['member_id']}"

    def test_no_duplicate_members(self, schedule):
        all_ids = []
        for day in schedule["days"]:
            for apt in day["appointments"]:
                all_ids.append(apt["member_id"])
        assert len(all_ids) == len(set(all_ids)), "Duplicate member_id in schedule"


class TestScheduleDemoRoles:
    def test_has_crossover_patient(self, schedule):
        crossover_count = sum(
            1 for d in schedule["days"]
            for a in d["appointments"]
            if a.get("demo_role") == "crossover_patient"
        )
        assert crossover_count == 1

    def test_has_feedback_patient(self, schedule):
        feedback_count = sum(
            1 for d in schedule["days"]
            for a in d["appointments"]
            if a.get("demo_role") == "feedback_patient"
        )
        assert feedback_count == 1

    def test_has_attribution_risk_patients(self, schedule):
        risk_count = sum(
            1 for d in schedule["days"]
            for a in d["appointments"]
            if "attribution_risk" in (a.get("demo_role") or "")
        )
        assert risk_count >= 3

    def test_all_demo_roles_valid(self, schedule):
        valid_roles = {
            "routine_low_gap", "moderate_gap", "high_gap", "hcc_opportunity",
            "attribution_risk_competing", "attribution_risk_enrollment",
            "attribution_new", "high_cost", "crossover_patient", "feedback_patient",
        }
        for day in schedule["days"]:
            for apt in day["appointments"]:
                assert apt["demo_role"] in valid_roles, f"Invalid demo_role: {apt['demo_role']}"
