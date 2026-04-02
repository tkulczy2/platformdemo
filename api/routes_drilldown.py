"""Provenance drill-down routes — the signature UX of the platform."""

from fastapi import APIRouter, HTTPException, Query

from api.main import (
    state,
    _fix_values,
    serialize_step_result,
    serialize_contract_clause,
    serialize_code_reference,
    serialize_member_detail,
)

router = APIRouter(prefix="/api/drilldown", tags=["drilldown"])


@router.get("/member/{member_id}")
def member_across_steps(member_id: str):
    """Find member details across all pipeline steps."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    member_info = {}
    for step in state.pipeline_result.steps:
        details = [d for d in step.member_details if d.member_id == member_id]
        if details:
            member_info[step.step_name] = {
                "step_number": step.step_number,
                "step_name": step.step_name,
                "details": [serialize_member_detail(d) for d in details],
                "contract_clauses": [serialize_contract_clause(c) for c in step.contract_clauses],
                "code_references": [serialize_code_reference(cr) for cr in step.code_references],
            }

    if not member_info:
        raise HTTPException(status_code=404, detail=f"Member {member_id} not found in any pipeline step.")

    return {
        "member_id": member_id,
        "steps": member_info,
    }


@router.get("/step/{step_num}/member/{member_id}")
def member_for_step(step_num: int, member_id: str):
    """Find member detail for a specific step."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    matching = [s for s in state.pipeline_result.steps if s.step_number == step_num]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Step {step_num} not found.")

    step = matching[0]
    details = [d for d in step.member_details if d.member_id == member_id]
    if not details:
        raise HTTPException(
            status_code=404,
            detail=f"Member {member_id} not found in step {step_num} ({step.step_name}).",
        )

    detail = details[0]
    serialized = serialize_member_detail(detail)

    return {
        "member_id": member_id,
        "step_number": step.step_number,
        "step": step.step_number,
        "step_name": step.step_name,
        "detail": {
            "outcome": serialized["outcome"],
            "outcome_value": serialized.get("reason", ""),
            "logic_trace": [serialized["reason"]] if serialized["reason"] else [],
            "flags": [],
            "intermediate_values": serialized.get("intermediate_values", []),
        },
        "data_references": serialized["data_references"],
        "contract_clauses": [serialize_contract_clause(c) for c in step.contract_clauses],
        "code_references": [serialize_code_reference(cr) for cr in step.code_references],
    }


@router.get("/step/{step_num}/members")
def members_for_step(
    step_num: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    """Paginated member list for a specific step."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    matching = [s for s in state.pipeline_result.steps if s.step_number == step_num]
    if not matching:
        raise HTTPException(status_code=404, detail=f"Step {step_num} not found.")

    step = matching[0]
    total = len(step.member_details)
    start = (page - 1) * page_size
    end = start + page_size
    page_details = step.member_details[start:end]

    return {
        "step_number": step.step_number,
        "step_name": step.step_name,
        "total_members": total,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "members": [serialize_member_detail(d) for d in page_details],
    }


# Map metric names to the step that produces them
METRIC_STEP_MAP = {
    "total_members": "eligibility",
    "eligible_count": "eligibility",
    "attributed_population": "attribution",
    "attributed_step1": "attribution",
    "attributed_step2": "attribution",
    "quality_composite": "quality",
    "actual_pmpm": "cost",
    "raw_pmpm": "cost",
    "total_member_months": "cost",
    "benchmark_pmpm": "settlement",
    "gross_savings": "settlement",
    "shared_savings_amount": "settlement",
    "settlement_status": "settlement",
    "msr_passed": "settlement",
    "quality_gate_passed": "settlement",
}

# Map step_N metric names to step names
STEP_NUM_MAP = {
    "step_1": "eligibility",
    "step_2": "attribution",
    "step_3": "quality",
    "step_4": "cost",
    "step_5": "settlement",
    "step_6": "reconciliation",
}


@router.get("/metric/{metric_name}")
def metric_drilldown(metric_name: str):
    """Drill into a specific metric — find the step that produces it and return details."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    # Check step_N names first
    target_step_name = STEP_NUM_MAP.get(metric_name)

    # Then check the static metric map
    if target_step_name is None:
        target_step_name = METRIC_STEP_MAP.get(metric_name)

    # If not in static map, check if it's a quality measure
    if target_step_name is None and metric_name.startswith("quality_"):
        target_step_name = "quality"

    if target_step_name is None:
        available = list(METRIC_STEP_MAP.keys()) + list(STEP_NUM_MAP.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Unknown metric: {metric_name}. Available metrics: {available}",
        )

    matching = [s for s in state.pipeline_result.steps if s.step_name == target_step_name]
    if not matching:
        available_steps = [s.step_name for s in state.pipeline_result.steps]
        raise HTTPException(
            status_code=404,
            detail=f"Step '{target_step_name}' not found in results. "
                   f"Available steps: {available_steps}. "
                   f"(Reconciliation only runs when a payer settlement report is loaded.)",
        )

    step = matching[0]
    metric_value = state.pipeline_result.final_metrics.get(metric_name)
    serialized = serialize_step_result(step)

    # Return flat structure matching what the frontend MetricData interface expects
    return {
        "metric_name": metric_name,
        "metric": metric_name,
        "metric_value": _fix_values(metric_value) if metric_value is not None else None,
        "value": _fix_values(metric_value) if metric_value is not None else None,
        "step_number": step.step_number,
        "step_name": step.step_name,
        "contract_clauses": serialized["contract_clauses"],
        "code_references": serialized["code_references"],
        "logic_summary": serialized["logic_summary"],
        "member_details": serialized["member_details"],
        "data_quality_flags": serialized["data_quality_flags"],
        "step": serialized,
    }
