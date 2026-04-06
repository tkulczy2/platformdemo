# Panel Intelligence Clinical View — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Clinical View tab to the VBC demo tool that generates pre-visit briefs from existing pipeline output, demonstrating the Panel Intelligence product concept.

**Architecture:** The Clinical View is a read-only consumer of the existing calculation engine. A schedule generator selects real members from the dataset matching narrative profiles. A brief engine transforms pipeline StepResult data into clinical briefs. New API endpoints serve briefs to a new React tab with schedule, brief, drill-down, and week-in-review screens.

**Tech Stack:** Python 3.11+ (pandas, FastAPI), React 18 + TypeScript, Tailwind CSS, Recharts. No new dependencies.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `data/contracts/hcc_mapping.json` | ICD-10 → HCC category mapping, RAF coefficients (top 30 HCCs) |
| `generator/clinical_schedule.py` | Generate one-week patient schedule from pipeline output |
| `engine/brief_engine.py` | Transform pipeline StepResult data into PatientBrief dataclasses |
| `api/routes_clinical.py` | 6 clinical view API endpoints |
| `frontend/src/components/clinical/ClinicalView.tsx` | Tab container with sub-routing |
| `frontend/src/components/clinical/WeeklySchedule.tsx` | Week-at-a-glance schedule |
| `frontend/src/components/clinical/PatientBrief.tsx` | Full pre-visit brief display |
| `frontend/src/components/clinical/BriefDrilldown.tsx` | Three-panel provenance drill-down |
| `frontend/src/components/clinical/WeekInReview.tsx` | Aggregate statistics summary |
| `frontend/src/components/clinical/FeedbackModal.tsx` | Provider feedback interaction |
| `tests/test_clinical_schedule.py` | Schedule validation tests |
| `tests/test_brief_engine.py` | Brief engine tests |

### Modified Files

| File | Change |
|------|--------|
| `api/main.py` | Add `AppState.clinical_feedback`, import+include clinical router |
| `frontend/src/App.tsx` | Add `/clinical/*` routes |
| `frontend/src/components/layout/AppShell.tsx` | Add "Clinical View" nav link |
| `frontend/src/api/client.ts` | Add clinical API client functions |
| `frontend/src/types/index.ts` | Add clinical view TypeScript types |

---

## Task 1: HCC Mapping Configuration

**Files:**
- Create: `data/contracts/hcc_mapping.json`

- [ ] **Step 1: Create the HCC mapping JSON file**

```json
{
  "description": "Simplified HCC mapping for demo purposes. Top 30 HCC categories with ICD-10 mappings and approximate RAF coefficients. Values are illustrative, not for clinical use.",
  "hcc_categories": {
    "HCC 18": {
      "condition_name": "Diabetes with Chronic Complications",
      "raf_coefficient": 0.302,
      "icd10_codes": ["E11.21", "E11.22", "E11.29", "E11.31", "E11.39", "E11.40", "E11.41", "E11.42", "E11.43", "E11.49", "E11.51", "E11.52", "E11.59", "E11.65"]
    },
    "HCC 19": {
      "condition_name": "Diabetes without Complication",
      "raf_coefficient": 0.105,
      "icd10_codes": ["E11.9", "E11.8", "E11.00", "E11.01"]
    },
    "HCC 85": {
      "condition_name": "Congestive Heart Failure",
      "raf_coefficient": 0.323,
      "icd10_codes": ["I50.1", "I50.20", "I50.21", "I50.22", "I50.23", "I50.30", "I50.31", "I50.32", "I50.33", "I50.40", "I50.41", "I50.42", "I50.43", "I50.9"]
    },
    "HCC 86": {
      "condition_name": "Acute Myocardial Infarction",
      "raf_coefficient": 0.231,
      "icd10_codes": ["I21.01", "I21.02", "I21.09", "I21.11", "I21.19", "I21.21", "I21.29", "I21.3", "I21.4", "I21.9"]
    },
    "HCC 96": {
      "condition_name": "Specified Heart Arrhythmias",
      "raf_coefficient": 0.259,
      "icd10_codes": ["I48.0", "I48.1", "I48.2", "I48.91"]
    },
    "HCC 108": {
      "condition_name": "COPD",
      "raf_coefficient": 0.335,
      "icd10_codes": ["J44.0", "J44.1", "J44.9"]
    },
    "HCC 111": {
      "condition_name": "Chronic Kidney Disease, Stage 4",
      "raf_coefficient": 0.289,
      "icd10_codes": ["N18.4"]
    },
    "HCC 112": {
      "condition_name": "Chronic Kidney Disease, Stage 5",
      "raf_coefficient": 0.289,
      "icd10_codes": ["N18.5", "N18.6"]
    },
    "HCC 22": {
      "condition_name": "Morbid Obesity",
      "raf_coefficient": 0.250,
      "icd10_codes": ["E66.01"]
    },
    "HCC 12": {
      "condition_name": "Breast / Prostate / Colorectal Cancer",
      "raf_coefficient": 0.146,
      "icd10_codes": ["C50.011", "C50.012", "C50.019", "C61", "C18.0", "C18.9", "C19", "C20"]
    },
    "HCC 55": {
      "condition_name": "Major Depression",
      "raf_coefficient": 0.309,
      "icd10_codes": ["F32.0", "F32.1", "F32.2", "F32.3", "F32.9", "F33.0", "F33.1", "F33.2", "F33.3", "F33.9"]
    },
    "HCC 40": {
      "condition_name": "Rheumatoid Arthritis",
      "raf_coefficient": 0.312,
      "icd10_codes": ["M05.70", "M05.79", "M06.00", "M06.09", "M06.9"]
    },
    "HCC 48": {
      "condition_name": "Coagulation Defects",
      "raf_coefficient": 0.192,
      "icd10_codes": ["D68.0", "D68.1", "D68.2", "D68.9"]
    },
    "HCC 59": {
      "condition_name": "Major Depressive and Bipolar Disorders",
      "raf_coefficient": 0.309,
      "icd10_codes": ["F31.0", "F31.1", "F31.2", "F31.30", "F31.31", "F31.32", "F31.9"]
    },
    "HCC 87": {
      "condition_name": "Unstable Angina",
      "raf_coefficient": 0.231,
      "icd10_codes": ["I20.0"]
    },
    "HCC 88": {
      "condition_name": "Angina Pectoris",
      "raf_coefficient": 0.140,
      "icd10_codes": ["I20.1", "I20.8", "I20.9", "I25.110", "I25.111", "I25.119"]
    },
    "HCC 99": {
      "condition_name": "Cerebral Atherosclerosis / Cerebrovascular Disease",
      "raf_coefficient": 0.230,
      "icd10_codes": ["I67.2", "I67.89", "I67.9"]
    },
    "HCC 100": {
      "condition_name": "Hemiplegia / Hemiparesis",
      "raf_coefficient": 0.481,
      "icd10_codes": ["G81.00", "G81.01", "G81.02", "G81.03", "G81.04", "G81.10", "G81.90"]
    },
    "HCC 103": {
      "condition_name": "Stroke",
      "raf_coefficient": 0.230,
      "icd10_codes": ["I63.00", "I63.10", "I63.20", "I63.30", "I63.40", "I63.50", "I63.9"]
    },
    "HCC 106": {
      "condition_name": "Atherosclerosis of Arteries of Extremities",
      "raf_coefficient": 0.299,
      "icd10_codes": ["I70.201", "I70.202", "I70.209", "I70.211", "I70.212", "I70.219"]
    },
    "HCC 114": {
      "condition_name": "Aspiration / Specified Bacterial Pneumonias",
      "raf_coefficient": 0.167,
      "icd10_codes": ["J69.0", "J15.0", "J15.1", "J15.20", "J15.211", "J15.212"]
    },
    "HCC 134": {
      "condition_name": "Dialysis Status",
      "raf_coefficient": 0.453,
      "icd10_codes": ["Z99.2"]
    },
    "HCC 135": {
      "condition_name": "Acute Renal Failure",
      "raf_coefficient": 0.453,
      "icd10_codes": ["N17.0", "N17.1", "N17.2", "N17.8", "N17.9"]
    },
    "HCC 136": {
      "condition_name": "Chronic Kidney Disease, Stage 3",
      "raf_coefficient": 0.069,
      "icd10_codes": ["N18.3"]
    },
    "HCC 161": {
      "condition_name": "Traumatic Amputation",
      "raf_coefficient": 0.588,
      "icd10_codes": ["S48.011A", "S48.012A", "S48.019A", "S48.111A", "S48.112A"]
    },
    "HCC 176": {
      "condition_name": "Artificial Openings for Feeding or Elimination",
      "raf_coefficient": 0.524,
      "icd10_codes": ["Z93.0", "Z93.1", "Z93.2", "Z93.3", "Z93.4"]
    },
    "HCC 21": {
      "condition_name": "Protein-Calorie Malnutrition",
      "raf_coefficient": 0.455,
      "icd10_codes": ["E43", "E44.0", "E44.1", "E46"]
    },
    "HCC 23": {
      "condition_name": "Other Significant Endocrine and Metabolic Disorders",
      "raf_coefficient": 0.250,
      "icd10_codes": ["E03.9", "E05.00", "E05.90", "E21.0", "E21.3", "E22.0"]
    },
    "HCC 47": {
      "condition_name": "Iron Deficiency and Other Anemias",
      "raf_coefficient": 0.192,
      "icd10_codes": ["D50.0", "D50.1", "D50.8", "D50.9", "D64.9"]
    },
    "HCC 138": {
      "condition_name": "Chronic Ulcer of Skin Except Pressure",
      "raf_coefficient": 0.535,
      "icd10_codes": ["L97.101", "L97.109", "L97.201", "L97.209", "L97.301", "L97.309"]
    }
  }
}
```

- [ ] **Step 2: Verify file is valid JSON**

Run: `python -c "import json; json.load(open('data/contracts/hcc_mapping.json')); print('Valid')"`
Expected: `Valid`

---

## Task 2: Clinical Schedule Generator

**Files:**
- Create: `generator/clinical_schedule.py`
- Create: `tests/test_clinical_schedule.py`

- [ ] **Step 1: Write the schedule generator tests**

```python
"""Tests for the clinical schedule generator."""

import json
from pathlib import Path

import pytest

from engine.data_loader import load_demo_data
from engine.pipeline import CalculationPipeline


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
    import pandas as pd
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

    def test_providers_are_pcps(self, schedule):
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
```

- [ ] **Step 2: Run the tests — confirm they skip (no schedule yet)**

Run: `python -m pytest tests/test_clinical_schedule.py -v 2>&1 | head -30`
Expected: Tests skip with "weekly_schedule.json not generated yet"

- [ ] **Step 3: Write the schedule generator**

```python
"""Generate a one-week clinical schedule for the Panel Intelligence demo.

Selects real members from the dataset who match the narrative profile required
for each day's demo story. Must be run AFTER the calculation pipeline has
produced output (depends on pipeline StepResult data for member classification).
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from engine.data_loader import LoadedData, load_demo_data
from engine.pipeline import CalculationPipeline
from engine.provenance import PipelineResult

DATA_DIR = Path(__file__).parent.parent / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
CONTRACTS_DIR = DATA_DIR / "contracts"
SCHEDULE_OUTPUT = SYNTHETIC_DIR / "weekly_schedule.json"

# Day-by-day appointment template: (demo_role, appointment_type)
DAY_TEMPLATES = {
    "Monday": {
        "narrative_theme": "Baseline Day",
        "appointments": [
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Annual Wellness"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("hcc_opportunity", "Follow-up"),
        ],
    },
    "Tuesday": {
        "narrative_theme": "Gap Closure Opportunity Day",
        "appointments": [
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("high_gap", "Follow-up"),
            ("high_gap", "Follow-up"),
            ("high_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Annual Wellness"),
            ("high_cost", "Follow-up"),
            ("crossover_patient", "Follow-up"),
        ],
    },
    "Wednesday": {
        "narrative_theme": "Attribution Risk Day",
        "appointments": [
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Annual Wellness"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("attribution_risk_competing", "Follow-up"),
            ("attribution_risk_enrollment", "Follow-up"),
            ("attribution_new", "New Patient"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
        ],
    },
    "Thursday": {
        "narrative_theme": "High-Cost Patient Day",
        "appointments": [
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Annual Wellness"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("high_cost", "Follow-up"),
            ("high_cost", "Follow-up"),
            ("attribution_risk_competing", "Follow-up"),
            ("attribution_risk_enrollment", "Follow-up"),
            ("high_gap", "Follow-up"),
        ],
    },
    "Friday": {
        "narrative_theme": "Week in Review Day",
        "appointments": [
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Annual Wellness"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("routine_low_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("moderate_gap", "Follow-up"),
            ("feedback_patient", "Follow-up"),
        ],
    },
}


def classify_members(
    pipeline_result: PipelineResult,
    data: LoadedData,
) -> dict[str, list[str]]:
    """Classify all members into demo-role categories based on pipeline output."""
    # Index pipeline data
    attribution_step = pipeline_result.steps[1]  # step 2
    quality_step = pipeline_result.steps[2]       # step 3
    cost_step = pipeline_result.steps[3]          # step 4

    # Build attributed set and details
    attributed_set = set(attribution_step.summary.get("attributed_population", []))
    attribution_details = attribution_step.summary.get("attribution_details", {})

    # Count quality gaps per member (outcome == "not_in_numerator")
    gap_counts: dict[str, int] = {}
    for md in quality_step.member_details:
        if md.outcome == "not_in_numerator":
            gap_counts[md.member_id] = gap_counts.get(md.member_id, 0) + 1

    # Cost data: member_id -> total_cost from member_details
    member_costs: dict[str, float] = {}
    for md in cost_step.member_details:
        member_costs[md.member_id] = md.intermediate_values.get("total_cost", 0)

    # For high cost threshold, use all attributed members' cost data
    all_costs = list(member_costs.values())
    cost_p90 = sorted(all_costs)[int(len(all_costs) * 0.9)] if all_costs else 0

    # Eligibility data for enrollment gaps
    eligibility = data.eligibility
    perf_start = pd.Timestamp("2025-01-01")
    perf_end = pd.Timestamp("2025-12-31")
    members_with_gaps = set()
    for mid in attributed_set:
        member_elig = eligibility[eligibility["member_id"] == mid]
        if len(member_elig) > 1:
            # Multiple enrollment periods = potential gap
            sorted_periods = member_elig.sort_values("enrollment_start_date")
            for i in range(len(sorted_periods) - 1):
                end_date = sorted_periods.iloc[i]["enrollment_end_date"]
                next_start = sorted_periods.iloc[i + 1]["enrollment_start_date"]
                if pd.notna(end_date) and pd.notna(next_start):
                    gap_days = (next_start - end_date).days
                    if gap_days > 30:
                        members_with_gaps.add(mid)
                        break

    # Competing provider analysis from claims
    claims = data.claims_professional
    qualifying_codes = set(["99201", "99202", "99203", "99204", "99205",
                           "99211", "99212", "99213", "99214", "99215"])
    perf_claims = claims[
        (claims["service_date"] >= perf_start) &
        (claims["service_date"] <= perf_end) &
        (claims["procedure_code"].isin(qualifying_codes))
    ]

    # Build provider lookup
    aco_npis = set(data.providers[data.providers["aco_participant"] == True]["npi"])
    competing_members = set()
    for mid in attributed_set:
        member_claims = perf_claims[perf_claims["member_id"] == mid]
        if member_claims.empty:
            continue
        non_aco = member_claims[~member_claims["rendering_npi"].isin(aco_npis)]
        aco = member_claims[member_claims["rendering_npi"].isin(aco_npis)]
        if len(non_aco) >= len(aco) and len(non_aco) >= 2:
            competing_members.add(mid)

    # Discrepancy crossover: find members with quality discrepancies
    reconciliation = pipeline_result.reconciliation or {}
    discrepancy_members = set()
    for disc in reconciliation.get("discrepancies", []):
        if disc.get("category") == "quality":
            discrepancy_members.add(disc.get("metric", ""))

    # Classify members
    classified: dict[str, list[str]] = {
        "routine_low_gap": [],
        "moderate_gap": [],
        "high_gap": [],
        "hcc_opportunity": [],
        "attribution_risk_competing": [],
        "attribution_risk_enrollment": [],
        "attribution_new": [],
        "high_cost": [],
        "crossover_patient": [],
        "feedback_patient": [],
    }

    for mid in attributed_set:
        gaps = gap_counts.get(mid, 0)
        cost = member_costs.get(mid, 0)

        if mid in competing_members:
            classified["attribution_risk_competing"].append(mid)
        elif mid in members_with_gaps:
            classified["attribution_risk_enrollment"].append(mid)
        elif cost >= cost_p90 and cost > 0:
            classified["high_cost"].append(mid)
        elif gaps >= 4:
            classified["high_gap"].append(mid)
        elif gaps >= 2:
            classified["moderate_gap"].append(mid)
        elif gaps == 1:
            # Could be routine_low_gap or hcc_opportunity
            classified["routine_low_gap"].append(mid)
        else:
            classified["routine_low_gap"].append(mid)

    # HCC opportunity: members with 0 gaps but have diagnosis codes that
    # could be HCC-relevant (simplified: attributed members with HCC risk > 1.0)
    members_df = data.members
    for mid in attributed_set:
        member_row = members_df[members_df["member_id"] == mid]
        if member_row.empty:
            continue
        hcc_score = member_row.iloc[0].get("hcc_risk_score", 0)
        if hcc_score and hcc_score > 1.2 and gap_counts.get(mid, 0) == 0:
            if mid not in competing_members and mid not in members_with_gaps:
                classified["hcc_opportunity"].append(mid)

    # Crossover: find members who are in the quality measure denominator
    # where the payer disagrees. Pick from moderate_gap members who have a
    # quality discrepancy scenario (measure that has a denominator difference).
    # We use moderate_gap members with colorectal screening gaps as best candidates.
    colorectal_gap_members = set()
    for md in quality_step.member_details:
        if md.outcome == "not_in_numerator" and "colorectal" in (md.reason or "").lower():
            colorectal_gap_members.add(md.member_id)
    crossover_candidates = [
        mid for mid in classified["moderate_gap"]
        if mid in colorectal_gap_members
    ]
    if not crossover_candidates:
        crossover_candidates = classified["moderate_gap"][:5]
    if crossover_candidates:
        classified["crossover_patient"] = [crossover_candidates[0]]

    # Feedback patient: a moderate_gap member with colorectal screening gap
    feedback_candidates = [
        mid for mid in classified["moderate_gap"]
        if mid in colorectal_gap_members and mid != (crossover_candidates[0] if crossover_candidates else "")
    ]
    if not feedback_candidates:
        feedback_candidates = [
            mid for mid in classified["moderate_gap"]
            if mid != (crossover_candidates[0] if crossover_candidates else "")
        ]
    if feedback_candidates:
        classified["feedback_patient"] = [feedback_candidates[0]]

    # Attribution new: members who were only recently attributed (step2 only
    # or low visit counts). Use members attributed in step2 as proxy.
    step2_members = []
    for md in attribution_step.member_details:
        if md.outcome == "attributed" and md.intermediate_values.get("attribution_step") == "step2":
            step2_members.append(md.member_id)
    classified["attribution_new"] = step2_members[:10]

    return classified


def generate_schedule(
    pipeline_result: PipelineResult,
    data: LoadedData,
    seed: int = 42,
) -> dict:
    """Generate the weekly clinical schedule."""
    rng = random.Random(seed)

    # Select 3 PCP providers
    providers_df = data.providers
    pcps = providers_df[(providers_df["is_pcp"] == True) & (providers_df["aco_participant"] == True)]
    selected_pcps = pcps.head(3)
    if len(selected_pcps) < 3:
        selected_pcps = providers_df[providers_df["aco_participant"] == True].head(3)

    provider_list = []
    for _, row in selected_pcps.iterrows():
        provider_list.append({
            "npi": row["npi"],
            "name": row["provider_name"],
            "specialty": row.get("specialty", "Family Medicine"),
            "panel_size": rng.randint(280, 360),
        })

    # Classify members
    classified = classify_members(pipeline_result, data)

    # Track used member IDs (no duplicates)
    used_members: set[str] = set()

    def pick_member(role: str) -> str | None:
        candidates = [m for m in classified.get(role, []) if m not in used_members]
        if not candidates:
            # Fallback to routine_low_gap
            candidates = [m for m in classified.get("routine_low_gap", []) if m not in used_members]
        if not candidates:
            return None
        member = rng.choice(candidates)
        used_members.add(member)
        return member

    # Demo notes per role
    demo_notes = {
        "routine_low_gap": "Routine visit, 0-1 open gaps. Establishes baseline brief experience.",
        "moderate_gap": "2-3 open quality gaps. Shows prioritization within the brief.",
        "high_gap": "4+ open quality gaps. Shows high-gap workflow.",
        "hcc_opportunity": "No open quality gaps but HCC recapture opportunity.",
        "attribution_risk_competing": "Competing provider visits detected. Attribution at risk.",
        "attribution_risk_enrollment": "Enrollment gap detected. Attribution continuity uncertain.",
        "attribution_new": "New panel attribution. First visit opportunity.",
        "high_cost": "Top decile cost. Shows cost context and utilization timeline.",
        "crossover_patient": "Quality gap + reconciliation discrepancy. Crossover between clinical and settlement views.",
        "feedback_patient": "Provider feedback demo. Patient may decline colorectal screening.",
    }

    # Build schedule
    week_start = datetime(2025, 10, 20)  # Monday
    days = []
    apt_counter = 0

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day_idx, day_name in enumerate(day_names):
        date = week_start + timedelta(days=day_idx)
        template = DAY_TEMPLATES[day_name]

        appointments = []
        # Build time slots: 08:30 start, 20-30 min slots, lunch 12:00-13:00
        slot_time = datetime(2025, 10, 20, 8, 30)
        provider_idx = 0

        for role, apt_type in template["appointments"]:
            apt_counter += 1
            member_id = pick_member(role)
            if member_id is None:
                continue

            # Advance time
            if slot_time.hour == 12:
                slot_time = slot_time.replace(hour=13, minute=0)

            appointments.append({
                "appointment_id": f"APT-{apt_counter:03d}",
                "time": slot_time.strftime("%H:%M"),
                "member_id": member_id,
                "provider_npi": provider_list[provider_idx % len(provider_list)]["npi"],
                "appointment_type": apt_type,
                "duration_minutes": rng.choice([20, 20, 30]),
                "demo_role": role,
                "demo_notes": demo_notes.get(role, ""),
            })

            # Advance slot
            slot_time += timedelta(minutes=rng.choice([20, 25, 30]))
            provider_idx += 1

        days.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_name": day_name,
            "narrative_theme": template["narrative_theme"],
            "appointments": appointments,
        })

    schedule = {
        "schedule_week": {
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": (week_start + timedelta(days=4)).strftime("%Y-%m-%d"),
            "practice_name": "Meridian Primary Care Associates",
            "providers": provider_list,
        },
        "days": days,
    }

    return schedule


def generate_and_save(seed: int = 42) -> dict:
    """Generate the schedule and save to disk."""
    data = load_demo_data()
    contract = json.load(open(CONTRACTS_DIR / "sample_mssp_contract.json"))
    payer_report = json.load(open(SYNTHETIC_DIR / "payer_settlement_report.json"))

    pipeline = CalculationPipeline()
    result = pipeline.run(data, contract, payer_report)

    schedule = generate_schedule(result, data, seed)

    with open(SCHEDULE_OUTPUT, "w") as f:
        json.dump(schedule, f, indent=2)

    total_apts = sum(len(d["appointments"]) for d in schedule["days"])
    print(f"Schedule generated: {total_apts} appointments across 5 days")
    print(f"Saved to: {SCHEDULE_OUTPUT}")

    return schedule


if __name__ == "__main__":
    generate_and_save()
```

- [ ] **Step 4: Run the schedule generator**

Run: `python -m generator.clinical_schedule`
Expected: Output showing ~50 appointments generated and saved to `data/synthetic/weekly_schedule.json`

- [ ] **Step 5: Run the schedule tests**

Run: `python -m pytest tests/test_clinical_schedule.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add data/contracts/hcc_mapping.json generator/clinical_schedule.py tests/test_clinical_schedule.py data/synthetic/weekly_schedule.json
git commit -m "feat: add clinical schedule generator and HCC mapping for Panel Intelligence"
```

---

## Task 3: Brief Engine — Data Classes and Core Assembly

**Files:**
- Create: `engine/brief_engine.py`
- Create: `tests/test_brief_engine.py`

- [ ] **Step 1: Write the brief engine tests**

```python
"""Tests for the brief engine — transforms pipeline output into clinical briefs."""

import json
from pathlib import Path

import pytest

from engine.brief_engine import BriefEngine, PatientBrief

SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"
CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "contracts"
SYNTHETIC_DIR = Path(__file__).parent.parent / "data" / "synthetic"


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
        "HEDIS", "PMPM", "attribution", "numerator", "denominator",
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
```

- [ ] **Step 2: Run tests — confirm they fail (module not found)**

Run: `python -m pytest tests/test_brief_engine.py -v 2>&1 | head -10`
Expected: ImportError — `engine.brief_engine` does not exist

- [ ] **Step 3: Write the brief engine**

```python
"""Brief Engine — transforms Platform calculation output into clinical pre-visit briefs.

This is a read-only transformation layer. It reads StepResult objects from the
existing pipeline and converts them into PatientBrief data structures for the
Clinical View. It never modifies the underlying data or calculation results.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from engine.provenance import PipelineResult

# Load HCC mapping
HCC_MAPPING_PATH = Path(__file__).parent.parent / "data" / "contracts" / "hcc_mapping.json"

# Clinical language translations — analytics terms to clinical terms
CLINICAL_TRANSLATIONS = {
    "attribution": "panel assignment",
    "Attribution": "Panel assignment",
    "attribution risk": "at risk of leaving your panel",
    "HEDIS measure": "screening",
    "HEDIS": "quality measure",
    "numerator": "completed",
    "denominator": "due for",
    "quality gap": "care action needed",
    "PMPM": "monthly care costs",
    "HCC recapture": "condition to document",
    "RAF score impact": "affects expected care needs assessment",
    "shared savings": "contract performance",
    "performance period": "contract year",
}

# Measure ID to clinical name mapping
MEASURE_CLINICAL_NAMES = {
    "hba1c_poor_control": "Diabetes Blood Sugar Control (HbA1c)",
    "controlling_bp": "Blood Pressure Control",
    "breast_cancer_screening": "Breast Cancer Screening (Mammogram)",
    "colorectal_screening": "Colorectal Cancer Screening",
    "depression_screening": "Depression Screening (PHQ-9)",
}

MEASURE_ACTIONS = {
    "hba1c_poor_control": "Review HbA1c results and adjust diabetes management plan",
    "controlling_bp": "Check blood pressure and adjust medication if needed",
    "breast_cancer_screening": "Order screening mammogram",
    "colorectal_screening": "Complete colorectal cancer screening (FIT kit or colonoscopy referral)",
    "depression_screening": "Complete depression screening (PHQ-9)",
}


def _translate(text: str) -> str:
    """Apply clinical language translations to text."""
    result = text
    for analytics_term, clinical_term in CLINICAL_TRANSLATIONS.items():
        result = result.replace(analytics_term, clinical_term)
    return result


@dataclass
class PriorityAction:
    rank: int
    action_text: str
    reason_text: str
    category: str
    measure_id: str | None = None
    financial_impact: float | None = None
    closable_this_visit: bool = False
    provenance: dict = field(default_factory=dict)


@dataclass
class QualityGap:
    measure_id: str
    measure_name: str
    action_needed: str
    closable_this_visit: bool
    days_remaining: int
    financial_weight: float
    priority_score: float
    provenance: dict = field(default_factory=dict)


@dataclass
class HccOpportunity:
    condition_name: str
    icd10_code: str
    hcc_category: str
    estimated_raf_impact: float
    evidence_source: str
    last_captured_date: str
    provenance: dict = field(default_factory=dict)


@dataclass
class UtilizationEvent:
    event_date: str
    event_type: str
    setting: str
    primary_diagnosis: str
    cost: float
    avoidable_flag: bool = False
    provenance: dict = field(default_factory=dict)


@dataclass
class AttributionRisk:
    status: str
    stability_score: float
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str | None = None
    competing_provider: dict | None = None
    days_since_last_visit: int = 0
    visits_this_year: int = 0
    provenance: dict = field(default_factory=dict)


@dataclass
class CostContext:
    ytd_cost: float = 0.0
    expected_cost: float = 0.0
    cost_status: str = "at_expected"
    cost_ratio: float = 1.0
    top_cost_driver: str | None = None
    pmpm: float = 0.0
    benchmark_pmpm: float = 0.0
    provenance: dict = field(default_factory=dict)


@dataclass
class PatientBrief:
    appointment_id: str
    member_id: str
    member_demographics: dict
    appointment_date: str
    appointment_time: str
    provider_name: str
    provider_npi: str
    contract_name: str
    performance_period_end: str
    days_remaining_in_period: int
    attribution_risk: AttributionRisk
    priority_actions: list[PriorityAction]
    quality_gaps: list[QualityGap]
    total_gap_count: int
    closable_this_visit_count: int
    hcc_opportunities: list[HccOpportunity]
    recent_utilization: list[UtilizationEvent]
    cost_context: CostContext
    demo_role: str
    is_crossover_patient: bool = False
    crossover_discrepancy: dict | None = None
    is_feedback_patient: bool = False


class BriefEngine:
    """Assembles PatientBrief objects from Platform calculation output.

    Usage:
        engine = BriefEngine(pipeline_result, contract_config, schedule)
        briefs = engine.generate_all_briefs()
        brief = engine.generate_brief("APT-001")
    """

    def __init__(self, pipeline_result: PipelineResult, contract_config: dict, schedule: dict):
        self._pipeline = pipeline_result
        self._contract = contract_config
        self._schedule = schedule
        self._perf_year = contract_config.get("performance_year", 2025)
        self._perf_end = f"{self._perf_year}-12-31"
        self._benchmark_pmpm = (
            contract_config.get("clauses", {})
            .get("settlement", {})
            .get("parameters", {})
            .get("benchmark_pmpm", 1187.0)
        )

        # Index pipeline output by member_id
        self._attribution_by_member = {}
        self._quality_by_member: dict[str, list] = {}
        self._cost_by_member = {}

        # Attribution
        attr_step = pipeline_result.steps[1]
        for md in attr_step.member_details:
            self._attribution_by_member[md.member_id] = md

        # Quality (multiple entries per member, one per measure)
        qual_step = pipeline_result.steps[2]
        for md in qual_step.member_details:
            self._quality_by_member.setdefault(md.member_id, []).append(md)

        # Cost
        cost_step = pipeline_result.steps[3]
        for md in cost_step.member_details:
            self._cost_by_member[md.member_id] = md

        # Reconciliation discrepancies
        self._reconciliation = pipeline_result.reconciliation or {}

        # Measure weights from contract
        qual_params = contract_config.get("clauses", {}).get("quality_measures", {}).get("parameters", {})
        self._measure_weights = qual_params.get("measure_weights", {})

        # Load HCC mapping
        self._hcc_mapping = {}
        if HCC_MAPPING_PATH.exists():
            with open(HCC_MAPPING_PATH) as f:
                hcc_data = json.load(f)
                self._hcc_mapping = hcc_data.get("hcc_categories", {})

        # Build provider name lookup from schedule
        self._provider_names = {}
        for p in schedule.get("schedule_week", {}).get("providers", []):
            self._provider_names[p["npi"]] = p["name"]

        # Attribution details from step summary
        self._attribution_details = attr_step.summary.get("attribution_details", {})

        # Overall cost summary
        self._cost_summary = cost_step.summary

    def generate_all_briefs(self) -> list[PatientBrief]:
        """Generate briefs for all appointments in the schedule."""
        briefs = []
        for day in self._schedule.get("days", []):
            for apt in day.get("appointments", []):
                brief = self.generate_brief(apt["appointment_id"])
                if brief:
                    briefs.append(brief)
        return briefs

    def generate_brief(self, appointment_id: str) -> PatientBrief | None:
        """Generate a single brief for one appointment."""
        appointment = self._find_appointment(appointment_id)
        if not appointment:
            return None

        member_id = appointment["member_id"]
        demo_role = appointment.get("demo_role", "routine_low_gap")

        # Calculate days remaining in performance period
        apt_date = appointment.get("_date", "2025-10-20")
        try:
            apt_dt = datetime.strptime(apt_date, "%Y-%m-%d")
            end_dt = datetime.strptime(self._perf_end, "%Y-%m-%d")
            days_remaining = max(0, (end_dt - apt_dt).days)
        except (ValueError, TypeError):
            days_remaining = 73

        attribution_risk = self._assess_attribution_risk(member_id, demo_role)
        quality_gaps = self._get_quality_gaps(member_id, days_remaining)
        hcc_opportunities = self._identify_hcc_opportunities(member_id)
        recent_utilization = self._get_recent_utilization(member_id)
        cost_context = self._get_cost_context(member_id)
        crossover = self._check_crossover(member_id, demo_role)

        priority_actions = self._prioritize_actions(
            attribution_risk, quality_gaps, hcc_opportunities, cost_context, days_remaining,
        )

        closable_count = sum(1 for g in quality_gaps if g.closable_this_visit)

        return PatientBrief(
            appointment_id=appointment_id,
            member_id=member_id,
            member_demographics=self._get_demographics(member_id),
            appointment_date=apt_date,
            appointment_time=appointment.get("time", ""),
            provider_name=self._provider_names.get(appointment.get("provider_npi", ""), "Provider"),
            provider_npi=appointment.get("provider_npi", ""),
            contract_name=self._contract.get("contract_name", "MSSP ACO Agreement"),
            performance_period_end=self._perf_end,
            days_remaining_in_period=days_remaining,
            attribution_risk=attribution_risk,
            priority_actions=priority_actions,
            quality_gaps=quality_gaps,
            total_gap_count=len(quality_gaps),
            closable_this_visit_count=closable_count,
            hcc_opportunities=hcc_opportunities,
            recent_utilization=recent_utilization,
            cost_context=cost_context,
            demo_role=demo_role,
            is_crossover_patient=crossover is not None,
            crossover_discrepancy=crossover,
            is_feedback_patient=(demo_role == "feedback_patient"),
        )

    def _find_appointment(self, appointment_id: str) -> dict | None:
        for day in self._schedule.get("days", []):
            for apt in day.get("appointments", []):
                if apt["appointment_id"] == appointment_id:
                    # Attach date context
                    apt["_date"] = day["date"]
                    return apt
        return None

    def _get_demographics(self, member_id: str) -> dict:
        """Get minimal demographics for the brief header."""
        # Extract from attribution detail if available
        attr_md = self._attribution_by_member.get(member_id)
        if attr_md:
            # Use intermediate values if available
            pass
        return {"member_id": member_id}

    def _assess_attribution_risk(self, member_id: str, demo_role: str) -> AttributionRisk:
        """Calculate attribution risk based on pipeline data and demo role."""
        attr_md = self._attribution_by_member.get(member_id)
        if not attr_md:
            return AttributionRisk(status="stable", stability_score=0.5, risk_factors=["Not found in calculation"])

        iv = attr_md.intermediate_values or {}
        visit_counts = iv.get("visit_counts_by_provider", {})
        attr_step = iv.get("attribution_step", "step1")
        attr_npi = iv.get("attributed_npi", "")

        # Count visits with attributed provider
        attr_visits = 0
        if attr_npi in visit_counts:
            attr_visits = visit_counts[attr_npi].get("count", 0)

        # Count total visits across all providers
        total_visits = sum(p.get("count", 0) for p in visit_counts.values())
        competing_visits = total_visits - attr_visits

        # Calculate stability score
        base_score = 1.0
        risk_factors = []

        # Factor: competing provider visits
        if competing_visits >= attr_visits and competing_visits >= 2:
            base_score -= 0.4
            risk_factors.append("Significant visits with providers outside your practice")

        # Factor: low visit count
        if attr_visits < 2:
            base_score -= 0.2
            risk_factors.append("Fewer than 2 visits this contract year")

        # Factor: Step 2 attribution (weaker relationship)
        if attr_step == "step2":
            base_score -= 0.1
            risk_factors.append("Newly assigned to your panel")

        # Override based on demo role for narrative purposes
        if "attribution_risk_competing" in demo_role:
            base_score = min(base_score, 0.35)
            if not any("outside" in f for f in risk_factors):
                risk_factors.append("Significant visits with providers outside your practice")
        elif "attribution_risk_enrollment" in demo_role:
            base_score = min(base_score, 0.45)
            if not any("enrollment" in f.lower() for f in risk_factors):
                risk_factors.append("Enrollment gap detected during the contract year")
        elif "attribution_new" in demo_role:
            base_score = 0.6  # Not "risk" per se, but noteworthy

        stability_score = max(0.0, min(1.0, base_score))

        # Status mapping
        if "attribution_new" in demo_role or attr_step == "step2":
            status = "new_attribution"
            recommended_action = "First visit opportunity — establish the care relationship"
        elif stability_score >= 0.7:
            status = "stable"
            recommended_action = None
        elif stability_score >= 0.4:
            status = "moderate_risk"
            recommended_action = "Schedule a follow-up visit within 30 days to strengthen the care relationship"
        else:
            status = "high_risk"
            recommended_action = "Schedule a retention visit. A qualifying visit today strengthens the care relationship."

        # Build competing provider info
        competing_provider = None
        if competing_visits > 0:
            for npi, info in visit_counts.items():
                if npi != attr_npi and info.get("count", 0) > 0:
                    competing_provider = {
                        "npi": npi,
                        "visit_count": info["count"],
                    }
                    break

        return AttributionRisk(
            status=status,
            stability_score=round(stability_score, 2),
            risk_factors=risk_factors,
            recommended_action=recommended_action,
            competing_provider=competing_provider,
            days_since_last_visit=0,
            visits_this_year=attr_visits,
            provenance={
                "step": "attribution",
                "step_number": 2,
                "member_id": member_id,
            },
        )

    def _get_quality_gaps(self, member_id: str, days_remaining: int) -> list[QualityGap]:
        """Get open quality gaps for this member in clinical language."""
        member_measures = self._quality_by_member.get(member_id, [])
        gaps = []

        for md in member_measures:
            if md.outcome != "not_in_numerator":
                continue

            # Determine which measure this is from
            measure_key = None
            for key in MEASURE_CLINICAL_NAMES:
                if key in (md.reason or "").lower() or key in str(md.intermediate_values):
                    measure_key = key
                    break

            # Try to extract measure from the step_name pattern
            if not measure_key:
                # The member_details from step_3 include details from each measure
                # We need to figure out which measure this belongs to
                reason_lower = (md.reason or "").lower()
                if "hba1c" in reason_lower or "diabetes" in reason_lower:
                    measure_key = "hba1c_poor_control"
                elif "blood pressure" in reason_lower or "bp" in reason_lower:
                    measure_key = "controlling_bp"
                elif "breast" in reason_lower or "mammog" in reason_lower:
                    measure_key = "breast_cancer_screening"
                elif "colorectal" in reason_lower or "colon" in reason_lower:
                    measure_key = "colorectal_screening"
                elif "depression" in reason_lower or "phq" in reason_lower:
                    measure_key = "depression_screening"

            if not measure_key:
                continue

            weight = self._measure_weights.get(measure_key, 0.2)
            closable = measure_key in {
                "controlling_bp", "depression_screening", "hba1c_poor_control"
            }

            # Priority score: financial_weight * urgency * closability
            urgency = min(1.0, max(0.1, 1.0 - (days_remaining / 365.0)))
            closability = 1.0 if closable else 0.5
            priority_score = round(weight * 0.4 + urgency * 0.3 + closability * 0.2 + (1 - days_remaining / 365) * 0.1, 3)

            gaps.append(QualityGap(
                measure_id=measure_key,
                measure_name=MEASURE_CLINICAL_NAMES.get(measure_key, measure_key),
                action_needed=MEASURE_ACTIONS.get(measure_key, f"Complete {measure_key} screening"),
                closable_this_visit=closable,
                days_remaining=days_remaining,
                financial_weight=weight,
                priority_score=priority_score,
                provenance={
                    "step": "quality",
                    "step_number": 3,
                    "member_id": member_id,
                    "measure_id": measure_key,
                },
            ))

        # Sort by priority score descending
        gaps.sort(key=lambda g: g.priority_score, reverse=True)
        return gaps

    def _identify_hcc_opportunities(self, member_id: str) -> list[HccOpportunity]:
        """Identify HCC recapture opportunities using the HCC mapping."""
        if not self._hcc_mapping:
            return []

        # Check claims for diagnosis codes that map to HCC categories
        # For the demo, we create opportunities for members with high HCC risk scores
        attr_md = self._attribution_by_member.get(member_id)
        if not attr_md:
            return []

        opportunities = []
        # Simplified: for members flagged as hcc_opportunity via demo_role,
        # we generate a plausible HCC opportunity from the mapping
        # In production this would scan diagnosis codes across claims and problem lists
        # For the demo, we pick from common HCCs based on member characteristics
        for hcc_cat, hcc_info in list(self._hcc_mapping.items())[:3]:
            if hcc_info["raf_coefficient"] > 0.2:
                opportunities.append(HccOpportunity(
                    condition_name=hcc_info["condition_name"],
                    icd10_code=hcc_info["icd10_codes"][0] if hcc_info["icd10_codes"] else "",
                    hcc_category=hcc_cat,
                    estimated_raf_impact=hcc_info["raf_coefficient"],
                    evidence_source="Prior year claims",
                    last_captured_date="2024-08-15",
                    provenance={"step": "quality", "step_number": 3, "member_id": member_id},
                ))
                break  # One opportunity per member for demo

        return opportunities

    def _get_recent_utilization(self, member_id: str) -> list[UtilizationEvent]:
        """Get recent utilization events (last 90 days) from cost data."""
        cost_md = self._cost_by_member.get(member_id)
        if not cost_md:
            return []

        # Build utilization events from data references
        events = []
        for ref in cost_md.data_references:
            source = ref.source_file
            if "facility" in source:
                events.append(UtilizationEvent(
                    event_date="2025-09-15",
                    event_type="Facility Visit",
                    setting="Acute Inpatient",
                    primary_diagnosis="Acute condition management",
                    cost=cost_md.intermediate_values.get("total_cost", 0) * 0.4,
                    avoidable_flag=False,
                    provenance={"step": "cost", "step_number": 4, "member_id": member_id},
                ))
            elif "professional" in source:
                events.append(UtilizationEvent(
                    event_date="2025-10-01",
                    event_type="Office Visit",
                    setting="Outpatient",
                    primary_diagnosis="Follow-up care",
                    cost=cost_md.intermediate_values.get("total_cost", 0) * 0.2,
                    avoidable_flag=False,
                    provenance={"step": "cost", "step_number": 4, "member_id": member_id},
                ))

        return events[:5]

    def _get_cost_context(self, member_id: str) -> CostContext:
        """Get cost trajectory context for the brief."""
        cost_md = self._cost_by_member.get(member_id)
        if not cost_md:
            return CostContext(benchmark_pmpm=self._benchmark_pmpm)

        iv = cost_md.intermediate_values
        total_cost = iv.get("total_cost", 0)
        member_months = iv.get("member_months", 12)
        member_pmpm = iv.get("member_pmpm", 0)

        # Expected cost based on benchmark
        expected = self._benchmark_pmpm * member_months

        ratio = total_cost / expected if expected > 0 else 1.0
        if ratio < 0.85:
            status = "below_expected"
            driver = None
        elif ratio <= 1.15:
            status = "at_expected"
            driver = None
        else:
            status = "above_expected"
            driver = "Inpatient admissions" if total_cost > expected * 1.3 else "Specialist visits"

        return CostContext(
            ytd_cost=round(total_cost, 2),
            expected_cost=round(expected, 2),
            cost_status=status,
            cost_ratio=round(ratio, 2),
            top_cost_driver=driver,
            pmpm=round(member_pmpm, 2),
            benchmark_pmpm=self._benchmark_pmpm,
            provenance={"step": "cost", "step_number": 4, "member_id": member_id},
        )

    def _check_crossover(self, member_id: str, demo_role: str) -> dict | None:
        """Check if this member has a reconciliation discrepancy."""
        if demo_role != "crossover_patient":
            return None

        # Find a quality discrepancy to link to
        for disc in self._reconciliation.get("discrepancies", []):
            if disc.get("category") == "quality":
                return {
                    "discrepancy_id": disc.get("id", ""),
                    "category": disc.get("category", ""),
                    "metric": disc.get("metric", ""),
                    "metric_label": disc.get("metric_label", ""),
                    "platform_value": disc.get("platform_value"),
                    "payer_value": disc.get("payer_value"),
                    "description": (
                        f"Your organization's calculation includes this patient in the "
                        f"{disc.get('metric_label', 'quality measure')} measure. "
                        f"The payer's settlement report disagrees. "
                        f"This discrepancy is documented in the Settlement Reconciliation view."
                    ),
                }
        return None

    def _prioritize_actions(
        self,
        attribution_risk: AttributionRisk,
        quality_gaps: list[QualityGap],
        hcc_opportunities: list[HccOpportunity],
        cost_context: CostContext,
        days_remaining: int,
    ) -> list[PriorityAction]:
        """Select top 3 priority actions using composite scoring."""
        candidates = []
        time_pressure = max(0.0, min(1.0, 1.0 - (days_remaining / 365.0)))

        # Quality gap actions
        for gap in quality_gaps:
            financial = gap.financial_weight  # Normalized 0-1
            urgency = 1.0  # Overdue screenings
            closability = 1.0 if gap.closable_this_visit else 0.5
            score = financial * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=gap.action_needed,
                reason_text=f"Closes 1 of {len(quality_gaps)} remaining care actions",
                category="gap_closure",
                measure_id=gap.measure_id,
                financial_impact=None,
                closable_this_visit=gap.closable_this_visit,
                provenance=gap.provenance,
            )))

        # HCC actions
        for hcc in hcc_opportunities:
            urgency = 0.8
            closability = 1.0  # Document in this visit
            score = 0.3 * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=f"Document {hcc.condition_name} if clinically appropriate",
                reason_text="Condition to document — supports accurate care needs assessment",
                category="hcc_recapture",
                closable_this_visit=True,
                provenance=hcc.provenance,
            )))

        # Attribution retention action
        if attribution_risk.status in ("moderate_risk", "high_risk"):
            urgency = 0.6
            closability = 0.3
            score = 0.2 * 0.4 + urgency * 0.3 + closability * 0.2 + time_pressure * 0.1

            candidates.append((score, PriorityAction(
                rank=0,
                action_text=attribution_risk.recommended_action or "Schedule a follow-up visit",
                reason_text="This patient is at risk of leaving your panel",
                category="attribution_retention",
                closable_this_visit=False,
                provenance=attribution_risk.provenance,
            )))

        # Sort by score and take top 3
        candidates.sort(key=lambda x: x[0], reverse=True)
        actions = []
        for i, (_, action) in enumerate(candidates[:3]):
            action.rank = i + 1
            actions.append(action)

        return actions
```

- [ ] **Step 4: Run the brief engine tests**

Run: `python -m pytest tests/test_brief_engine.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add engine/brief_engine.py tests/test_brief_engine.py
git commit -m "feat: add brief engine for clinical pre-visit brief generation"
```

---

## Task 4: Clinical View API Endpoints

**Files:**
- Create: `api/routes_clinical.py`
- Modify: `api/main.py`

- [ ] **Step 1: Create the clinical routes module**

```python
"""Clinical View API endpoints — pre-visit briefs and schedule."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from dataclasses import asdict

from api.main import state, _fix_values

router = APIRouter(prefix="/api/clinical", tags=["clinical"])

# In-memory cache for BriefEngine and schedule
_brief_engine = None
_schedule = None
_briefs_cache: dict = {}
_feedback_store: dict = {}  # appointment_id -> {item_type, item_id, feedback, note}

SCHEDULE_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "weekly_schedule.json"
CONTRACTS_DIR = Path(__file__).parent.parent / "data" / "contracts"


def _get_schedule() -> dict:
    global _schedule
    if _schedule is None:
        if not SCHEDULE_PATH.exists():
            raise HTTPException(404, "Schedule not generated. Run: python -m generator.clinical_schedule")
        with open(SCHEDULE_PATH) as f:
            _schedule = json.load(f)
    return _schedule


def _get_brief_engine():
    global _brief_engine
    if _brief_engine is not None:
        return _brief_engine

    if state.pipeline_result is None:
        raise HTTPException(400, "Pipeline has not been run. Run calculation first.")

    schedule = _get_schedule()
    contract = state.contract
    if contract is None:
        contract_path = CONTRACTS_DIR / "sample_mssp_contract.json"
        with open(contract_path) as f:
            contract = json.load(f)

    from engine.brief_engine import BriefEngine
    _brief_engine = BriefEngine(state.pipeline_result, contract, schedule)
    return _brief_engine


def _brief_to_dict(brief) -> dict:
    """Convert a PatientBrief dataclass to a JSON-serializable dict."""
    return _fix_values(asdict(brief))


@router.get("/schedule")
def get_schedule():
    """Returns the full weekly schedule."""
    return _get_schedule()


@router.get("/schedule/{date}")
def get_day_schedule(date: str):
    """Returns a single day's schedule."""
    schedule = _get_schedule()
    for day in schedule.get("days", []):
        if day["date"] == date:
            return day
    raise HTTPException(404, f"No schedule found for date {date}")


@router.get("/brief/{appointment_id}")
def get_brief(appointment_id: str):
    """Returns the full PatientBrief for one appointment."""
    engine = _get_brief_engine()
    if appointment_id not in _briefs_cache:
        brief = engine.generate_brief(appointment_id)
        if brief is None:
            raise HTTPException(404, f"Appointment {appointment_id} not found")
        _briefs_cache[appointment_id] = brief

    brief = _briefs_cache[appointment_id]
    result = _brief_to_dict(brief)

    # Overlay any feedback
    if appointment_id in _feedback_store:
        result["feedback"] = _feedback_store[appointment_id]

    return result


@router.get("/brief/{appointment_id}/drilldown/{item_type}/{item_id}")
def get_brief_drilldown(appointment_id: str, item_type: str, item_id: str):
    """Returns provenance detail for a specific brief item."""
    engine = _get_brief_engine()
    if appointment_id not in _briefs_cache:
        brief = engine.generate_brief(appointment_id)
        if brief is None:
            raise HTTPException(404, f"Appointment {appointment_id} not found")
        _briefs_cache[appointment_id] = brief

    brief = _briefs_cache[appointment_id]

    # Find the item and return its provenance
    if item_type == "gap":
        for gap in brief.quality_gaps:
            if gap.measure_id == item_id:
                return {
                    "item_type": "gap",
                    "item_id": item_id,
                    "detail": _fix_values(asdict(gap)),
                    "provenance": gap.provenance,
                    "clinical_question": f"Why is {gap.measure_name} showing as due for this patient?",
                }
    elif item_type == "hcc":
        for hcc in brief.hcc_opportunities:
            if hcc.hcc_category == item_id:
                return {
                    "item_type": "hcc",
                    "item_id": item_id,
                    "detail": _fix_values(asdict(hcc)),
                    "provenance": hcc.provenance,
                    "clinical_question": f"Why is {hcc.condition_name} flagged for documentation?",
                }
    elif item_type == "attribution":
        return {
            "item_type": "attribution",
            "item_id": "attribution_risk",
            "detail": _fix_values(asdict(brief.attribution_risk)),
            "provenance": brief.attribution_risk.provenance,
            "clinical_question": "What is this patient's panel assignment status?",
        }
    elif item_type == "cost":
        return {
            "item_type": "cost",
            "item_id": "cost_context",
            "detail": _fix_values(asdict(brief.cost_context)),
            "provenance": brief.cost_context.provenance,
            "clinical_question": "What does this patient's cost trajectory look like?",
        }
    elif item_type == "priority_action":
        idx = int(item_id) - 1 if item_id.isdigit() else 0
        if 0 <= idx < len(brief.priority_actions):
            action = brief.priority_actions[idx]
            return {
                "item_type": "priority_action",
                "item_id": item_id,
                "detail": _fix_values(asdict(action)),
                "provenance": action.provenance,
                "clinical_question": f"Why is '{action.action_text}' the #{action.rank} priority?",
            }

    raise HTTPException(404, f"Item {item_type}/{item_id} not found in brief {appointment_id}")


@router.get("/week-summary")
def get_week_summary():
    """Returns aggregate statistics for the week."""
    engine = _get_brief_engine()
    schedule = _get_schedule()

    # Generate all briefs
    all_briefs = engine.generate_all_briefs()

    total_encounters = len(all_briefs)
    attributed_encounters = sum(1 for b in all_briefs if b.attribution_risk.status != "")
    total_gaps = sum(b.total_gap_count for b in all_briefs)
    closable_gaps = sum(b.closable_this_visit_count for b in all_briefs)
    patients_with_gaps = sum(1 for b in all_briefs if b.total_gap_count > 0)
    at_risk_patients = sum(1 for b in all_briefs if b.attribution_risk.status in ("moderate_risk", "high_risk"))

    # Measure-level gap breakdown
    measure_gaps: dict[str, dict] = {}
    for brief in all_briefs:
        for gap in brief.quality_gaps:
            if gap.measure_id not in measure_gaps:
                measure_gaps[gap.measure_id] = {
                    "measure_name": gap.measure_name,
                    "gap_count": 0,
                    "closable_count": 0,
                }
            measure_gaps[gap.measure_id]["gap_count"] += 1
            if gap.closable_this_visit:
                measure_gaps[gap.measure_id]["closable_count"] += 1

    # Cost summary
    costs = [b.cost_context.ytd_cost for b in all_briefs if b.cost_context.ytd_cost > 0]
    avg_cost = sum(costs) / len(costs) if costs else 0
    high_cost_count = sum(1 for b in all_briefs if b.cost_context.cost_status == "above_expected")

    # Crossover
    crossover_brief = next((b for b in all_briefs if b.is_crossover_patient), None)

    # Feedback
    feedback_entries = list(_feedback_store.values())

    return {
        "total_encounters": total_encounters,
        "attributed_encounters": attributed_encounters,
        "total_gaps_addressable": total_gaps,
        "closable_this_week": closable_gaps,
        "patients_with_gaps": patients_with_gaps,
        "at_risk_patients": at_risk_patients,
        "measure_gaps": measure_gaps,
        "cost_summary": {
            "average_ytd_cost": round(avg_cost, 2),
            "high_cost_patients": high_cost_count,
            "benchmark_pmpm": engine._benchmark_pmpm,
        },
        "crossover": {
            "exists": crossover_brief is not None,
            "member_id": crossover_brief.member_id if crossover_brief else None,
            "discrepancy": crossover_brief.crossover_discrepancy if crossover_brief else None,
        },
        "feedback": feedback_entries,
    }


@router.post("/feedback/{appointment_id}")
def submit_feedback(appointment_id: str, body: dict):
    """Records provider feedback on a brief recommendation."""
    _feedback_store[appointment_id] = {
        "appointment_id": appointment_id,
        "item_type": body.get("item_type", ""),
        "item_id": body.get("item_id", ""),
        "feedback": body.get("feedback", ""),
        "note": body.get("note", ""),
    }
    return {"status": "success", "feedback": _feedback_store[appointment_id]}
```

- [ ] **Step 2: Register the clinical router in api/main.py**

Add to `api/main.py` after the existing router imports:
```python
from api.routes_clinical import router as clinical_router
```

And after the existing `app.include_router` calls:
```python
app.include_router(clinical_router)
```

- [ ] **Step 3: Verify the API starts and endpoints are accessible**

Run: `python -c "from api.routes_clinical import router; print('Import OK')"` 
Expected: `Import OK`

- [ ] **Step 4: Commit**

```bash
git add api/routes_clinical.py api/main.py
git commit -m "feat: add clinical view API endpoints for briefs and schedule"
```

---

## Task 5: Frontend — Types, API Client, and Navigation

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add clinical view types to `frontend/src/types/index.ts`**

Append to the end of the file:
```typescript
// ---------------------------------------------------------------------------
// Clinical View (Panel Intelligence)
// ---------------------------------------------------------------------------

export interface ScheduleWeek {
  start_date: string;
  end_date: string;
  practice_name: string;
  providers: ScheduleProvider[];
}

export interface ScheduleProvider {
  npi: string;
  name: string;
  specialty: string;
  panel_size: number;
}

export interface ScheduleDay {
  date: string;
  day_name: string;
  narrative_theme: string;
  appointments: Appointment[];
}

export interface Appointment {
  appointment_id: string;
  time: string;
  member_id: string;
  provider_npi: string;
  appointment_type: string;
  duration_minutes: number;
  demo_role: string;
  demo_notes: string;
}

export interface WeeklySchedule {
  schedule_week: ScheduleWeek;
  days: ScheduleDay[];
}

export interface AttributionRiskInfo {
  status: 'stable' | 'moderate_risk' | 'high_risk' | 'new_attribution';
  stability_score: number;
  risk_factors: string[];
  recommended_action: string | null;
  competing_provider: { npi: string; visit_count: number } | null;
  days_since_last_visit: number;
  visits_this_year: number;
}

export interface PriorityActionInfo {
  rank: number;
  action_text: string;
  reason_text: string;
  category: string;
  measure_id: string | null;
  financial_impact: number | null;
  closable_this_visit: boolean;
}

export interface QualityGapInfo {
  measure_id: string;
  measure_name: string;
  action_needed: string;
  closable_this_visit: boolean;
  days_remaining: number;
  financial_weight: number;
  priority_score: number;
}

export interface HccOpportunityInfo {
  condition_name: string;
  icd10_code: string;
  hcc_category: string;
  estimated_raf_impact: number;
  evidence_source: string;
  last_captured_date: string;
}

export interface UtilizationEventInfo {
  event_date: string;
  event_type: string;
  setting: string;
  primary_diagnosis: string;
  cost: number;
  avoidable_flag: boolean;
}

export interface CostContextInfo {
  ytd_cost: number;
  expected_cost: number;
  cost_status: 'below_expected' | 'at_expected' | 'above_expected';
  cost_ratio: number;
  top_cost_driver: string | null;
  pmpm: number;
  benchmark_pmpm: number;
}

export interface PatientBriefResponse {
  appointment_id: string;
  member_id: string;
  member_demographics: Record<string, unknown>;
  appointment_date: string;
  appointment_time: string;
  provider_name: string;
  provider_npi: string;
  contract_name: string;
  performance_period_end: string;
  days_remaining_in_period: number;
  attribution_risk: AttributionRiskInfo;
  priority_actions: PriorityActionInfo[];
  quality_gaps: QualityGapInfo[];
  total_gap_count: number;
  closable_this_visit_count: number;
  hcc_opportunities: HccOpportunityInfo[];
  recent_utilization: UtilizationEventInfo[];
  cost_context: CostContextInfo;
  demo_role: string;
  is_crossover_patient: boolean;
  crossover_discrepancy: Record<string, unknown> | null;
  is_feedback_patient: boolean;
  feedback?: Record<string, string>;
}

export interface WeekSummary {
  total_encounters: number;
  attributed_encounters: number;
  total_gaps_addressable: number;
  closable_this_week: number;
  patients_with_gaps: number;
  at_risk_patients: number;
  measure_gaps: Record<string, { measure_name: string; gap_count: number; closable_count: number }>;
  cost_summary: { average_ytd_cost: number; high_cost_patients: number; benchmark_pmpm: number };
  crossover: { exists: boolean; member_id: string | null; discrepancy: Record<string, unknown> | null };
  feedback: Array<Record<string, string>>;
}
```

- [ ] **Step 2: Add clinical API client functions to `frontend/src/api/client.ts`**

Append before the Response type aliases section:
```typescript
// ---------------------------------------------------------------------------
// Clinical View endpoints
// ---------------------------------------------------------------------------

export async function getClinicalSchedule() {
  return request<WeeklyScheduleResponse>('/api/clinical/schedule');
}

export async function getClinicalDaySchedule(date: string) {
  return request<DayScheduleResponse>(`/api/clinical/schedule/${date}`);
}

export async function getClinicalBrief(appointmentId: string) {
  return request<PatientBriefApiResponse>(`/api/clinical/brief/${appointmentId}`);
}

export async function getClinicalBriefDrilldown(
  appointmentId: string,
  itemType: string,
  itemId: string,
) {
  return request<BriefDrilldownResponse>(
    `/api/clinical/brief/${appointmentId}/drilldown/${itemType}/${itemId}`,
  );
}

export async function getClinicalWeekSummary() {
  return request<WeekSummaryResponse>('/api/clinical/week-summary');
}

export async function submitClinicalFeedback(
  appointmentId: string,
  feedback: { item_type: string; item_id: string; feedback: string; note?: string },
) {
  return request<{ status: string }>(`/api/clinical/feedback/${appointmentId}`, {
    method: 'POST',
    body: JSON.stringify(feedback),
  });
}
```

And add these to the response type aliases section:
```typescript
interface WeeklyScheduleResponse {
  schedule_week: { start_date: string; end_date: string; practice_name: string; providers: Array<Record<string, unknown>> };
  days: Array<Record<string, unknown>>;
}

interface DayScheduleResponse {
  date: string;
  day_name: string;
  narrative_theme: string;
  appointments: Array<Record<string, unknown>>;
}

interface PatientBriefApiResponse extends Record<string, unknown> {
  appointment_id: string;
  member_id: string;
}

interface BriefDrilldownResponse {
  item_type: string;
  item_id: string;
  detail: Record<string, unknown>;
  provenance: Record<string, unknown>;
  clinical_question: string;
}

interface WeekSummaryResponse extends Record<string, unknown> {
  total_encounters: number;
}
```

- [ ] **Step 3: Add Clinical View nav link to AppShell**

In `frontend/src/components/layout/AppShell.tsx`, update the `NAV_LINKS` array:
```typescript
const NAV_LINKS = [
  { label: 'Data', path: '/' },
  { label: 'Contract', path: '/contract' },
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Reconciliation', path: '/reconciliation' },
  { label: 'Clinical View', path: '/clinical' },
];
```

- [ ] **Step 4: Add clinical routes to App.tsx**

```typescript
import { Routes, Route } from 'react-router-dom';
import AppShell from '@/components/layout/AppShell';
import DataUpload from '@/components/upload/DataUpload';
import ContractEditor from '@/components/contract/ContractEditor';
import ResultsDashboard from '@/components/dashboard/ResultsDashboard';
import DrilldownView from '@/components/drilldown/DrilldownView';
import ReconciliationView from '@/components/reconciliation/ReconciliationView';
import ClinicalView from '@/components/clinical/ClinicalView';

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DataUpload />} />
        <Route path="/contract" element={<ContractEditor />} />
        <Route path="/dashboard" element={<ResultsDashboard />} />
        <Route path="/drilldown/:stepNum/:memberId" element={<DrilldownView />} />
        <Route path="/drilldown/metric/:metricName" element={<DrilldownView />} />
        <Route path="/reconciliation" element={<ReconciliationView />} />
        <Route path="/clinical/*" element={<ClinicalView />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/components/layout/AppShell.tsx frontend/src/App.tsx
git commit -m "feat: add clinical view types, API client, and navigation"
```

---

## Task 6: Frontend — Clinical View Components

**Files:**
- Create: `frontend/src/components/clinical/ClinicalView.tsx`
- Create: `frontend/src/components/clinical/WeeklySchedule.tsx`
- Create: `frontend/src/components/clinical/PatientBrief.tsx`
- Create: `frontend/src/components/clinical/BriefDrilldown.tsx`
- Create: `frontend/src/components/clinical/WeekInReview.tsx`
- Create: `frontend/src/components/clinical/FeedbackModal.tsx`

These components follow the existing codebase patterns: Tailwind CSS for styling, `classNames` utility, `formatCurrency`/`formatPercent`/`formatNumber` from `@/utils/formatters`, and the API client from `@/api/client`.

- [ ] **Step 1: Create ClinicalView.tsx (tab container with sub-routing)**

```typescript
import { useState } from 'react';
import WeeklySchedule from './WeeklySchedule';
import PatientBrief from './PatientBrief';
import BriefDrilldown from './BriefDrilldown';
import WeekInReview from './WeekInReview';

type ClinicalScreen = 'schedule' | 'brief' | 'drilldown' | 'review';

interface DrilldownTarget {
  appointmentId: string;
  itemType: string;
  itemId: string;
}

export default function ClinicalView() {
  const [screen, setScreen] = useState<ClinicalScreen>('schedule');
  const [selectedAppointment, setSelectedAppointment] = useState<string | null>(null);
  const [drilldownTarget, setDrilldownTarget] = useState<DrilldownTarget | null>(null);

  function handleSelectAppointment(appointmentId: string) {
    setSelectedAppointment(appointmentId);
    setScreen('brief');
  }

  function handleDrilldown(appointmentId: string, itemType: string, itemId: string) {
    setDrilldownTarget({ appointmentId, itemType, itemId });
    setScreen('drilldown');
  }

  function handleBack() {
    if (screen === 'drilldown') {
      setScreen('brief');
    } else if (screen === 'brief') {
      setScreen('schedule');
    } else if (screen === 'review') {
      setScreen('schedule');
    }
  }

  return (
    <div>
      {screen === 'schedule' && (
        <WeeklySchedule
          onSelectAppointment={handleSelectAppointment}
          onShowReview={() => setScreen('review')}
        />
      )}
      {screen === 'brief' && selectedAppointment && (
        <PatientBrief
          appointmentId={selectedAppointment}
          onBack={handleBack}
          onDrilldown={(itemType, itemId) =>
            handleDrilldown(selectedAppointment, itemType, itemId)
          }
        />
      )}
      {screen === 'drilldown' && drilldownTarget && (
        <BriefDrilldown
          appointmentId={drilldownTarget.appointmentId}
          itemType={drilldownTarget.itemType}
          itemId={drilldownTarget.itemId}
          onBack={handleBack}
        />
      )}
      {screen === 'review' && <WeekInReview onBack={handleBack} />}
    </div>
  );
}
```

- [ ] **Step 2: Create WeeklySchedule.tsx**

```typescript
import { useEffect, useState } from 'react';
import { getClinicalSchedule } from '@/api/client';
import { classNames } from '@/utils/formatters';

const STATUS_COLORS: Record<string, string> = {
  stable: 'bg-green-400',
  moderate_risk: 'bg-yellow-400',
  high_risk: 'bg-red-400',
  new_attribution: 'bg-blue-400',
};

const ROLE_BADGE: Record<string, string> = {
  crossover_patient: 'ring-2 ring-purple-400',
  feedback_patient: 'ring-2 ring-teal-400',
};

interface Props {
  onSelectAppointment: (id: string) => void;
  onShowReview: () => void;
}

export default function WeeklySchedule({ onSelectAppointment, onShowReview }: Props) {
  const [schedule, setSchedule] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getClinicalSchedule();
        setSchedule(data as Record<string, unknown>);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load schedule');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading clinical schedule...</span>
      </div>
    );
  }

  if (error || !schedule) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700 mb-2">{error || 'No schedule data'}</p>
        <p className="text-xs text-red-500">Run the pipeline and generate the schedule first.</p>
      </div>
    );
  }

  const week = schedule.schedule_week as Record<string, unknown>;
  const days = schedule.days as Array<Record<string, unknown>>;
  const providers = (week.providers as Array<Record<string, unknown>>) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            {week.practice_name as string}
          </h2>
          <p className="text-sm text-gray-500">
            Week of {week.start_date as string} — {week.end_date as string}
          </p>
          <div className="flex gap-4 mt-1">
            {providers.map((p) => (
              <span key={p.npi as string} className="text-xs text-gray-400">
                {p.name as string} ({p.panel_size as number} patients)
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onShowReview}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 hover:bg-teal-100 ring-1 ring-inset ring-teal-200"
        >
          Week in Review
        </button>
      </div>

      {/* Day columns */}
      <div className="grid grid-cols-5 gap-3">
        {days.map((day) => {
          const apts = (day.appointments as Array<Record<string, unknown>>) || [];
          return (
            <div
              key={day.date as string}
              className="rounded-xl border border-gray-200 bg-white overflow-hidden"
            >
              <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
                <p className="text-sm font-semibold text-gray-900">
                  {day.day_name as string}
                </p>
                <p className="text-xs text-gray-400">{day.date as string}</p>
                <p className="text-[10px] text-gray-400 italic mt-0.5">
                  {day.narrative_theme as string}
                </p>
                <span className="inline-flex items-center rounded-full bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 mt-1">
                  {apts.length} patients
                </span>
              </div>
              <div className="divide-y divide-gray-50 max-h-[60vh] overflow-y-auto">
                {apts.map((apt) => {
                  const role = apt.demo_role as string;
                  return (
                    <button
                      key={apt.appointment_id as string}
                      onClick={() => onSelectAppointment(apt.appointment_id as string)}
                      className={classNames(
                        'w-full text-left px-3 py-2 hover:bg-teal-50 transition-colors',
                        ROLE_BADGE[role] || '',
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-gray-500">
                          {apt.time as string}
                        </span>
                        <div className="flex items-center gap-1">
                          <span
                            className={classNames(
                              'h-2 w-2 rounded-full',
                              STATUS_COLORS.stable,
                            )}
                          />
                        </div>
                      </div>
                      <p className="text-xs text-gray-700 mt-0.5 truncate">
                        {apt.member_id as string}
                      </p>
                      <p className="text-[10px] text-gray-400 truncate">
                        {apt.appointment_type as string}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-gray-400">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-400" /> Stable</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-yellow-400" /> Moderate Risk</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-400" /> High Risk</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-400" /> New to Panel</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create PatientBrief.tsx**

```typescript
import { useEffect, useState } from 'react';
import { getClinicalBrief, submitClinicalFeedback } from '@/api/client';
import { classNames, formatCurrency } from '@/utils/formatters';
import FeedbackModal from './FeedbackModal';
import type {
  PatientBriefResponse,
  PriorityActionInfo,
  QualityGapInfo,
  AttributionRiskInfo,
  CostContextInfo,
} from '@/types';

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  stable: { bg: 'bg-green-50', text: 'text-green-700', label: 'Stable' },
  moderate_risk: { bg: 'bg-yellow-50', text: 'text-yellow-700', label: 'At Risk' },
  high_risk: { bg: 'bg-red-50', text: 'text-red-700', label: 'High Risk' },
  new_attribution: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'New to Panel' },
};

const STATUS_DOT: Record<string, string> = {
  stable: 'bg-green-400',
  moderate_risk: 'bg-yellow-400',
  high_risk: 'bg-red-400',
  new_attribution: 'bg-blue-400',
};

interface Props {
  appointmentId: string;
  onBack: () => void;
  onDrilldown: (itemType: string, itemId: string) => void;
}

export default function PatientBrief({ appointmentId, onBack, onDrilldown }: Props) {
  const [brief, setBrief] = useState<PatientBriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<{ type: string; id: string } | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await getClinicalBrief(appointmentId);
        setBrief(data as unknown as PatientBriefResponse);
      } catch {
        setBrief(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [appointmentId]);

  async function handleFeedbackSubmit(feedback: string, note: string) {
    if (!feedbackTarget) return;
    await submitClinicalFeedback(appointmentId, {
      item_type: feedbackTarget.type,
      item_id: feedbackTarget.id,
      feedback,
      note,
    });
    setFeedbackOpen(false);
    // Reload brief to show updated state
    const data = await getClinicalBrief(appointmentId);
    setBrief(data as unknown as PatientBriefResponse);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading brief...</span>
      </div>
    );
  }

  if (!brief) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-red-600">Brief not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">
          Back to schedule
        </button>
      </div>
    );
  }

  const attrStyle = STATUS_STYLES[brief.attribution_risk.status] || STATUS_STYLES.stable;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to schedule
      </button>

      {/* Header Bar */}
      <div className={classNames('rounded-xl p-4', attrStyle.bg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-900">
              {brief.member_id}
            </span>
            <span className="text-xs text-gray-500">
              {brief.appointment_date} at {brief.appointment_time}
            </span>
            <span className="text-xs text-gray-500">{brief.provider_name}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className={classNames('h-2.5 w-2.5 rounded-full', STATUS_DOT[brief.attribution_risk.status] || 'bg-gray-400')} />
              <span className={classNames('text-xs font-medium', attrStyle.text)}>
                {attrStyle.label}
              </span>
            </div>
            <span className="rounded-full bg-white/80 px-2.5 py-1 text-xs font-medium text-gray-700">
              {brief.days_remaining_in_period} days remaining
            </span>
          </div>
        </div>
      </div>

      {/* Priority Actions */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Priority Actions</h3>
        {brief.priority_actions.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
            <p className="text-sm text-gray-500">No priority actions for this encounter. Routine visit.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {brief.priority_actions.map((action: PriorityActionInfo) => (
              <button
                key={action.rank}
                onClick={() => onDrilldown('priority_action', String(action.rank))}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-4 hover:border-teal-300 hover:bg-teal-50/30 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center h-7 w-7 rounded-full bg-teal-100 text-teal-700 text-sm font-bold">
                    {action.rank}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{action.action_text}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{action.reason_text}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                        {action.category.replace('_', ' ')}
                      </span>
                      {action.closable_this_visit && (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">
                          Can close today
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Quality Gaps */}
      {brief.quality_gaps.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Care Actions Due
            <span className="ml-2 text-xs font-normal text-gray-400">
              {brief.closable_this_visit_count} of {brief.total_gap_count} can be closed today
            </span>
          </h3>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Measure</th>
                  <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Action Needed</th>
                  <th className="px-3 py-2 text-center text-[10px] font-semibold text-gray-500 uppercase">Today?</th>
                  <th className="px-3 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {brief.quality_gaps.map((gap: QualityGapInfo) => (
                  <tr
                    key={gap.measure_id}
                    onClick={() => onDrilldown('gap', gap.measure_id)}
                    className="hover:bg-teal-50/30 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2 text-xs text-gray-900">{gap.measure_name}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{gap.action_needed}</td>
                    <td className="px-3 py-2 text-center">
                      {gap.closable_this_visit ? (
                        <svg className="h-4 w-4 text-green-500 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="h-4 w-4 text-gray-300 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className={classNames(
                        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                        gap.priority_score > 0.6 ? 'bg-red-100 text-red-700' :
                        gap.priority_score > 0.4 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600',
                      )}>
                        {gap.priority_score > 0.6 ? 'High' : gap.priority_score > 0.4 ? 'Medium' : 'Low'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {brief.is_feedback_patient && (
            <button
              onClick={() => {
                const gap = brief.quality_gaps[0];
                if (gap) {
                  setFeedbackTarget({ type: 'gap', id: gap.measure_id });
                  setFeedbackOpen(true);
                }
              }}
              className="mt-2 text-xs text-teal-600 hover:text-teal-700 font-medium"
            >
              Mark a recommendation as addressed or declined
            </button>
          )}
        </section>
      )}

      {/* HCC Opportunities */}
      {brief.hcc_opportunities.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Conditions to Document</h3>
          <div className="space-y-2">
            {brief.hcc_opportunities.map((hcc) => (
              <button
                key={hcc.hcc_category}
                onClick={() => onDrilldown('hcc', hcc.hcc_category)}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-3 hover:border-teal-300 transition-colors"
              >
                <p className="text-sm text-gray-900">{hcc.condition_name}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  <span className="font-mono">{hcc.icd10_code}</span> — Document if clinically appropriate
                </p>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Cost Context */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Cost Context</h3>
        <div
          onClick={() => onDrilldown('cost', 'cost_context')}
          className="rounded-lg border border-gray-200 bg-white p-4 cursor-pointer hover:border-teal-300 transition-colors"
        >
          <CostGauge context={brief.cost_context} />
        </div>
      </section>

      {/* Attribution Note */}
      {brief.attribution_risk.status !== 'stable' && (
        <div className={classNames(
          'rounded-lg p-4',
          brief.attribution_risk.status === 'new_attribution' ? 'bg-blue-50 border border-blue-200' :
          brief.attribution_risk.status === 'moderate_risk' ? 'bg-yellow-50 border border-yellow-200' :
          'bg-red-50 border border-red-200',
        )}>
          <div className="flex items-start gap-2">
            <svg className="h-4 w-4 text-current flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <div>
              {brief.attribution_risk.risk_factors.map((f, i) => (
                <p key={i} className="text-xs text-gray-700">{f}</p>
              ))}
              {brief.attribution_risk.recommended_action && (
                <p className="text-xs font-medium text-gray-900 mt-1">
                  {brief.attribution_risk.recommended_action}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Crossover Banner */}
      {brief.is_crossover_patient && brief.crossover_discrepancy && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <div className="flex items-center gap-2 mb-1">
            <svg className="h-4 w-4 text-purple-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            <span className="text-xs font-semibold text-purple-700">Settlement Reconciliation Connection</span>
          </div>
          <p className="text-xs text-purple-600">
            {(brief.crossover_discrepancy as Record<string, unknown>).description as string}
          </p>
        </div>
      )}

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        onSubmit={handleFeedbackSubmit}
      />
    </div>
  );
}

function CostGauge({ context }: { context: CostContextInfo }) {
  const pct = Math.min(200, Math.max(0, context.cost_ratio * 100));
  const barWidth = Math.min(100, pct / 2);

  return (
    <div>
      <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
        <span>Below Expected</span>
        <span>At Expected</span>
        <span>Above Expected</span>
      </div>
      <div className="relative h-3 rounded-full bg-gray-100 overflow-hidden">
        <div className="absolute inset-y-0 left-1/2 w-px bg-gray-300" />
        <div
          className={classNames(
            'absolute inset-y-0 left-0 rounded-full transition-all',
            context.cost_status === 'below_expected' ? 'bg-green-400' :
            context.cost_status === 'at_expected' ? 'bg-gray-400' : 'bg-red-400',
          )}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-600">
          YTD: {formatCurrency(context.ytd_cost)}
        </span>
        {context.top_cost_driver && (
          <span className="text-xs text-red-600">
            Driver: {context.top_cost_driver}
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create BriefDrilldown.tsx**

```typescript
import { useEffect, useState } from 'react';
import { getClinicalBriefDrilldown, getSourceCode } from '@/api/client';

interface Props {
  appointmentId: string;
  itemType: string;
  itemId: string;
  onBack: () => void;
}

export default function BriefDrilldown({ appointmentId, itemType, itemId, onBack }: Props) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [sourceCode, setSourceCode] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const dd = await getClinicalBriefDrilldown(appointmentId, itemType, itemId);
        setData(dd as Record<string, unknown>);

        // Try to load source code from provenance
        const prov = dd.provenance as Record<string, unknown>;
        if (prov?.step) {
          try {
            const module = `step_${prov.step_number}_${prov.step}`;
            const func = prov.step === 'quality' ? 'calculate_quality_measures' :
                         prov.step === 'attribution' ? 'assign_attribution' :
                         prov.step === 'cost' ? 'calculate_cost' : '';
            if (func) {
              const code = await getSourceCode(module, func);
              setSourceCode(code.source || '');
            }
          } catch { /* Code loading is optional */ }
        }
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [appointmentId, itemType, itemId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading provenance...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-gray-500">Drilldown data not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">Back</button>
      </div>
    );
  }

  const detail = data.detail as Record<string, unknown>;
  const question = data.clinical_question as string;

  return (
    <div className="space-y-4">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to brief
      </button>

      {/* Clinical question header */}
      <div className="rounded-lg bg-teal-50 border border-teal-200 px-4 py-3">
        <p className="text-sm font-medium text-teal-800">{question}</p>
      </div>

      {/* Three-panel layout */}
      <div className="grid grid-cols-3 gap-4 min-h-[50vh]">
        {/* Contract Language */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Contract Language</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto">
            <p className="text-xs text-gray-700 leading-relaxed">
              {detail.provenance
                ? JSON.stringify((data.provenance as Record<string, unknown>), null, 2)
                : 'Contract clause reference available in full Platform view.'}
            </p>
          </div>
        </div>

        {/* Interpretation + Data */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Interpretation & Data</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto space-y-3">
            {Object.entries(detail).map(([key, value]) => {
              if (key === 'provenance') return null;
              return (
                <div key={key}>
                  <p className="text-[10px] font-semibold text-gray-400 uppercase">{key.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-gray-700 mt-0.5">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Code */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Code</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto">
            {sourceCode ? (
              <pre className="text-[11px] text-gray-700 font-mono whitespace-pre-wrap leading-relaxed">
                {sourceCode}
              </pre>
            ) : (
              <p className="text-xs text-gray-400 italic">
                Source code available when running with live API.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create WeekInReview.tsx**

```typescript
import { useEffect, useState } from 'react';
import { getClinicalWeekSummary } from '@/api/client';
import { formatCurrency, formatNumber } from '@/utils/formatters';
import type { WeekSummary } from '@/types';

interface Props {
  onBack: () => void;
}

export default function WeekInReview({ onBack }: Props) {
  const [summary, setSummary] = useState<WeekSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getClinicalWeekSummary();
        setSummary(data as unknown as WeekSummary);
      } catch {
        setSummary(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading week summary...</span>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-gray-500">Week summary not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">Back</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mb-2"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Back to schedule
          </button>
          <h2 className="text-lg font-semibold text-gray-900">Week in Review</h2>
        </div>
      </div>

      {/* Key Numbers */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total Encounters', value: formatNumber(summary.total_encounters) },
          { label: 'Patients with Gaps', value: formatNumber(summary.patients_with_gaps) },
          { label: 'Gaps Addressable', value: formatNumber(summary.total_gaps_addressable) },
          { label: 'Closable This Week', value: formatNumber(summary.closable_this_week) },
          { label: 'At-Risk Patients', value: formatNumber(summary.at_risk_patients) },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-[10px] text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Quality Gap Breakdown */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Quality Measure Gaps This Week</h3>
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Measure</th>
                <th className="px-4 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Gaps Found</th>
                <th className="px-4 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Closable</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {Object.entries(summary.measure_gaps).map(([id, info]) => (
                <tr key={id}>
                  <td className="px-4 py-2 text-xs text-gray-900">{info.measure_name}</td>
                  <td className="px-4 py-2 text-xs text-gray-700 text-right">{info.gap_count}</td>
                  <td className="px-4 py-2 text-xs text-green-700 text-right">{info.closable_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Cost Summary */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Cost Summary</h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatCurrency(summary.cost_summary.average_ytd_cost)}
            </p>
            <p className="text-[10px] text-gray-500">Avg YTD Cost</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatNumber(summary.cost_summary.high_cost_patients)}
            </p>
            <p className="text-[10px] text-gray-500">High-Cost Patients</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatCurrency(summary.cost_summary.benchmark_pmpm)}
            </p>
            <p className="text-[10px] text-gray-500">Benchmark PMPM</p>
          </div>
        </div>
      </section>

      {/* Crossover Section */}
      {summary.crossover.exists && (
        <section className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">Settlement Reconciliation Connection</h3>
          <p className="text-xs text-purple-600">
            Patient {summary.crossover.member_id} seen this week has an open care action AND a discrepancy
            in the Settlement Reconciliation view. One engine, two audiences, one source of truth.
          </p>
        </section>
      )}

      {/* Feedback Section */}
      {summary.feedback.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Provider Feedback</h3>
          {summary.feedback.map((fb, i) => (
            <div key={i} className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-xs text-teal-700">
              Feedback on {fb.item_type}/{fb.item_id}: <strong>{fb.feedback}</strong>
              {fb.note && <span className="text-teal-500"> — {fb.note}</span>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Create FeedbackModal.tsx**

```typescript
import { useState } from 'react';
import { classNames } from '@/utils/formatters';

const OPTIONS = [
  { value: 'completed', label: 'Completed', description: 'Gap was closed during the encounter' },
  { value: 'patient_declined', label: 'Patient Declined', description: 'Patient was offered but declined' },
  { value: 'clinically_inappropriate', label: 'Clinically Inappropriate', description: 'Recommendation not applicable' },
  { value: 'already_addressed', label: 'Already Addressed', description: 'Data is stale — already done' },
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (feedback: string, note: string) => void;
}

export default function FeedbackModal({ isOpen, onClose, onSubmit }: Props) {
  const [selected, setSelected] = useState<string>('');
  const [note, setNote] = useState('');

  if (!isOpen) return null;

  function handleSubmit() {
    if (selected) {
      onSubmit(selected, note);
      setSelected('');
      setNote('');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Provider Feedback</h3>

        <div className="space-y-2 mb-4">
          {OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSelected(opt.value)}
              className={classNames(
                'w-full text-left rounded-lg border p-3 transition-colors',
                selected === opt.value
                  ? 'border-teal-300 bg-teal-50'
                  : 'border-gray-200 hover:bg-gray-50',
              )}
            >
              <p className="text-sm font-medium text-gray-900">{opt.label}</p>
              <p className="text-xs text-gray-500">{opt.description}</p>
            </button>
          ))}
        </div>

        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional note..."
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-700 placeholder:text-gray-400 focus:border-teal-300 focus:ring-1 focus:ring-teal-300 mb-4"
          rows={2}
        />

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selected}
            className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700 disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`
Expected: No type errors (or only pre-existing ones)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/clinical/
git commit -m "feat: add Clinical View frontend components for Panel Intelligence"
```

---

## Task 7: Update CLAUDE.md with Phase 5

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add Phase 5 to CLAUDE.md**

After the Phase 4 section in the Build Order, add Phase 5 documentation. Also add the new files to the Project Structure section and new endpoints to the API Endpoint Reference.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Phase 5 Panel Intelligence to CLAUDE.md"
```

---

## Task 8: Integration Testing

- [ ] **Step 1: Run all existing tests to confirm no regressions**

Run: `python -m pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 2: Run the clinical schedule tests**

Run: `python -m pytest tests/test_clinical_schedule.py -v`
Expected: All PASS

- [ ] **Step 3: Run the brief engine tests**

Run: `python -m pytest tests/test_brief_engine.py -v`
Expected: All PASS

- [ ] **Step 4: Verify API endpoints manually**

Run: `python -c "
from fastapi.testclient import TestClient
from api.main import app, state
from engine.data_loader import load_demo_data
from engine.pipeline import CalculationPipeline
import json

# Setup
data = load_demo_data()
contract = json.load(open('data/contracts/sample_mssp_contract.json'))
payer_report = json.load(open('data/synthetic/payer_settlement_report.json'))
pipeline = CalculationPipeline()
state.data = data
state.contract = contract
state.pipeline_result = pipeline.run(data, contract, payer_report)
state.payer_report = payer_report

client = TestClient(app)

# Test endpoints
r = client.get('/api/clinical/schedule')
assert r.status_code == 200, f'Schedule: {r.status_code}'
schedule = r.json()
print(f'Schedule: {len(schedule[\"days\"])} days')

apt_id = schedule['days'][0]['appointments'][0]['appointment_id']
r = client.get(f'/api/clinical/brief/{apt_id}')
assert r.status_code == 200, f'Brief: {r.status_code}'
brief = r.json()
print(f'Brief for {apt_id}: {len(brief[\"priority_actions\"])} actions, {brief[\"total_gap_count\"]} gaps')

r = client.get('/api/clinical/week-summary')
assert r.status_code == 200, f'Summary: {r.status_code}'
summary = r.json()
print(f'Week summary: {summary[\"total_encounters\"]} encounters, {summary[\"total_gaps_addressable\"]} gaps')

print('All clinical API endpoints working!')
"`

Expected: All endpoints return 200 with valid data

- [ ] **Step 5: Verify frontend compiles**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: Build succeeds

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: Phase 5 Panel Intelligence — complete implementation"
```
