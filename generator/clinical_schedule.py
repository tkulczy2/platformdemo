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
    attribution_step = pipeline_result.steps[1]  # step 2
    quality_step = pipeline_result.steps[2]       # step 3
    cost_step = pipeline_result.steps[3]          # step 4

    # Build attributed set
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

    # High cost threshold
    all_costs = list(member_costs.values())
    cost_p90 = sorted(all_costs)[int(len(all_costs) * 0.9)] if all_costs else 0

    # Enrollment gaps
    eligibility = data.eligibility
    members_with_gaps = set()
    for mid in attributed_set:
        member_elig = eligibility[eligibility["member_id"] == mid]
        if len(member_elig) > 1:
            sorted_periods = member_elig.sort_values("enrollment_start_date")
            for i in range(len(sorted_periods) - 1):
                end_date = sorted_periods.iloc[i]["enrollment_end_date"]
                next_start = sorted_periods.iloc[i + 1]["enrollment_start_date"]
                if pd.notna(end_date) and pd.notna(next_start):
                    gap_days = (next_start - end_date).days
                    if gap_days > 30:
                        members_with_gaps.add(mid)
                        break

    # Competing provider analysis
    claims = data.claims_professional
    qualifying_codes = {"99201", "99202", "99203", "99204", "99205",
                        "99211", "99212", "99213", "99214", "99215"}
    perf_start = pd.Timestamp("2025-01-01")
    perf_end = pd.Timestamp("2025-12-31")
    perf_claims = claims[
        (claims["service_date"] >= perf_start) &
        (claims["service_date"] <= perf_end) &
        (claims["procedure_code"].isin(qualifying_codes))
    ]

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

    # Colorectal screening gaps (for crossover/feedback candidates)
    colorectal_gap_members = set()
    for md in quality_step.member_details:
        if md.outcome == "not_in_numerator" and "colorectal" in (md.reason or "").lower():
            colorectal_gap_members.add(md.member_id)

    # Step 2 attributed (new attribution proxy)
    step2_members = []
    for md in attribution_step.member_details:
        if md.outcome == "attributed" and md.intermediate_values.get("attribution_step") == "step2":
            step2_members.append(md.member_id)

    # Classify
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
        else:
            classified["routine_low_gap"].append(mid)

    # HCC opportunity: high risk score, 0 gaps, not already classified
    already_classified = set()
    for role_list in classified.values():
        already_classified.update(role_list)

    members_df = data.members
    for mid in attributed_set:
        if mid in already_classified:
            continue
        member_row = members_df[members_df["member_id"] == mid]
        if member_row.empty:
            continue
        hcc_score = member_row.iloc[0].get("hcc_risk_score", 0)
        if hcc_score and hcc_score > 1.2 and gap_counts.get(mid, 0) == 0:
            classified["hcc_opportunity"].append(mid)
        else:
            classified["routine_low_gap"].append(mid)

    # Crossover patient: moderate_gap with colorectal gap
    crossover_candidates = [
        mid for mid in classified["moderate_gap"]
        if mid in colorectal_gap_members
    ]
    if not crossover_candidates:
        crossover_candidates = classified["moderate_gap"][:5]
    if crossover_candidates:
        classified["crossover_patient"] = [crossover_candidates[0]]

    # Feedback patient: different moderate_gap member with colorectal gap
    crossover_id = crossover_candidates[0] if crossover_candidates else ""
    feedback_candidates = [
        mid for mid in classified["moderate_gap"]
        if mid in colorectal_gap_members and mid != crossover_id
    ]
    if not feedback_candidates:
        feedback_candidates = [
            mid for mid in classified["moderate_gap"]
            if mid != crossover_id
        ]
    if feedback_candidates:
        classified["feedback_patient"] = [feedback_candidates[0]]

    # Attribution new: step2 attributed members
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

    classified = classify_members(pipeline_result, data)

    # Track used member IDs
    used_members: set[str] = set()

    def pick_member(role: str) -> str | None:
        candidates = [m for m in classified.get(role, []) if m not in used_members]
        if not candidates:
            candidates = [m for m in classified.get("routine_low_gap", []) if m not in used_members]
        if not candidates:
            return None
        member = rng.choice(candidates)
        used_members.add(member)
        return member

    demo_notes = {
        "routine_low_gap": "Routine visit, 0-1 open gaps. Establishes baseline brief experience.",
        "moderate_gap": "2-3 open quality gaps. Shows prioritization within the brief.",
        "high_gap": "4+ open quality gaps. Shows high-gap workflow.",
        "hcc_opportunity": "No open quality gaps but HCC recapture opportunity.",
        "attribution_risk_competing": "Competing provider visits detected. At risk of leaving panel.",
        "attribution_risk_enrollment": "Enrollment gap detected. Care relationship continuity uncertain.",
        "attribution_new": "New panel member. First visit opportunity.",
        "high_cost": "Top decile cost. Shows cost context and utilization timeline.",
        "crossover_patient": "Quality gap + reconciliation discrepancy. Crossover between clinical and settlement views.",
        "feedback_patient": "Provider feedback demo. Patient may decline colorectal screening.",
    }

    week_start = datetime(2025, 10, 20)  # Monday
    days = []
    apt_counter = 0

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day_idx, day_name in enumerate(day_names):
        date = week_start + timedelta(days=day_idx)
        template = DAY_TEMPLATES[day_name]

        appointments = []
        slot_time = datetime(2025, 10, 20, 8, 30)
        provider_idx = 0

        for role, apt_type in template["appointments"]:
            apt_counter += 1
            member_id = pick_member(role)
            if member_id is None:
                continue

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

            slot_time += timedelta(minutes=rng.choice([20, 25, 30]))
            provider_idx += 1

        days.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_name": day_name,
            "narrative_theme": template["narrative_theme"],
            "appointments": appointments,
        })

    return {
        "schedule_week": {
            "start_date": week_start.strftime("%Y-%m-%d"),
            "end_date": (week_start + timedelta(days=4)).strftime("%Y-%m-%d"),
            "practice_name": "Meridian Primary Care Associates",
            "providers": provider_list,
        },
        "days": days,
    }


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
