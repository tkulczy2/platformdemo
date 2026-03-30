"""Pipeline calculation and results routes."""

from fastapi import APIRouter, HTTPException

from engine.pipeline import CalculationPipeline

from api.main import state, serialize_step_result, _fix_values

router = APIRouter(prefix="/api", tags=["calculate"])


@router.post("/calculate")
def run_calculation():
    """Run the full calculation pipeline with current data + contract."""
    if state.data is None:
        raise HTTPException(status_code=400, detail="No data loaded. Upload data or load demo data first.")
    if state.contract is None:
        raise HTTPException(status_code=400, detail="No contract loaded. Configure contract or load demo contract first.")

    pipeline = CalculationPipeline()
    try:
        result = pipeline.run(state.data, state.contract, state.payer_report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {e}")

    state.pipeline_result = result

    return {
        "status": "success",
        "total_execution_time_ms": result.total_execution_time_ms,
        "steps_completed": len(result.steps),
        "final_metrics": _fix_values(result.final_metrics),
        "has_reconciliation": result.reconciliation is not None,
    }


@router.get("/results/summary")
def results_summary():
    """Return top-level metrics from the pipeline result."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    result = state.pipeline_result
    return {
        "final_metrics": _fix_values(result.final_metrics),
        "total_execution_time_ms": result.total_execution_time_ms,
        "steps": [
            {
                "step_number": step.step_number,
                "step_name": step.step_name,
                "execution_time_ms": step.execution_time_ms,
                "member_count": len(step.member_details),
                "data_quality_flags": step.data_quality_flags,
            }
            for step in result.steps
        ],
    }


@router.get("/results/step/{step_num}")
def results_step(step_num: int):
    """Return the full StepResult for a specific step (1-indexed)."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    matching = [s for s in state.pipeline_result.steps if s.step_number == step_num]
    if not matching:
        raise HTTPException(
            status_code=404,
            detail=f"Step {step_num} not found. Available steps: "
                   f"{[s.step_number for s in state.pipeline_result.steps]}",
        )

    return serialize_step_result(matching[0])
