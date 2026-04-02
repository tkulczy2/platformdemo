"""Clinical View API endpoints — pre-visit briefs and schedule."""

import json
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.main import state, _fix_values

router = APIRouter(prefix="/api/clinical", tags=["clinical"])

# In-memory cache
_brief_engine = None
_schedule = None
_briefs_cache: dict = {}
_feedback_store: dict = {}

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

    all_briefs = engine.generate_all_briefs()

    total_encounters = len(all_briefs)
    attributed_encounters = sum(1 for b in all_briefs if b.attribution_risk.status != "")
    total_gaps = sum(b.total_gap_count for b in all_briefs)
    closable_gaps = sum(b.closable_this_visit_count for b in all_briefs)
    patients_with_gaps = sum(1 for b in all_briefs if b.total_gap_count > 0)
    at_risk_patients = sum(1 for b in all_briefs if b.attribution_risk.status in ("moderate_risk", "high_risk"))

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

    costs = [b.cost_context.ytd_cost for b in all_briefs if b.cost_context.ytd_cost > 0]
    avg_cost = sum(costs) / len(costs) if costs else 0
    high_cost_count = sum(1 for b in all_briefs if b.cost_context.cost_status == "above_expected")

    crossover_brief = next((b for b in all_briefs if b.is_crossover_patient), None)

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
        "feedback": list(_feedback_store.values()),
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
