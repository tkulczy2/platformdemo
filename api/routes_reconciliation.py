"""Reconciliation routes — compare platform results to payer settlement."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from api.main import state, _fix_values

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])

PAYER_REPORT_PATH = Path(__file__).parent.parent / "data" / "synthetic" / "payer_settlement_report.json"


@router.post("/load-demo")
def load_demo_payer_report():
    """Load the pre-built demo payer settlement report."""
    if not PAYER_REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="Demo payer settlement report not found. Run generator first.")

    state.payer_report = json.loads(PAYER_REPORT_PATH.read_text())
    # Clear pipeline result so reconciliation is re-run with payer report
    state.pipeline_result = None

    return {
        "status": "success",
        "message": "Demo payer settlement report loaded",
        "report_keys": list(state.payer_report.keys()),
    }


@router.post("/upload")
async def upload_payer_report(file: UploadFile = File(...)):
    """Upload a payer settlement report (JSON)."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Payer report must be a JSON file.")

    content = await file.read()
    try:
        state.payer_report = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # Clear pipeline result so reconciliation is re-run with new payer report
    state.pipeline_result = None

    return {
        "status": "success",
        "message": "Payer settlement report uploaded",
        "report_keys": list(state.payer_report.keys()) if isinstance(state.payer_report, dict) else [],
    }


@router.get("/summary")
def reconciliation_summary():
    """Return reconciliation summary from pipeline result."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    recon = state.pipeline_result.reconciliation
    if recon is None:
        raise HTTPException(
            status_code=404,
            detail="No reconciliation data. Upload a payer settlement report and re-run the pipeline.",
        )

    return _fix_values({
        "discrepancy_count": recon.get("discrepancy_count", 0),
        "total_financial_impact": recon.get("total_financial_impact", 0),
        "categories": recon.get("categories", {}),
        "execution_time_ms": recon.get("execution_time_ms", 0),
    })


@router.get("/detail/{category}")
def reconciliation_detail(category: str):
    """Return discrepancies filtered by category."""
    if state.pipeline_result is None:
        raise HTTPException(status_code=404, detail="No pipeline results available. Run /api/calculate first.")

    recon = state.pipeline_result.reconciliation
    if recon is None:
        raise HTTPException(
            status_code=404,
            detail="No reconciliation data. Upload a payer settlement report and re-run the pipeline.",
        )

    discrepancies = recon.get("discrepancies", [])
    filtered = [d for d in discrepancies if d.get("category") == category]

    if not filtered:
        available = list({d.get("category") for d in discrepancies})
        raise HTTPException(
            status_code=404,
            detail=f"No discrepancies found for category '{category}'. Available categories: {available}",
        )

    return _fix_values({
        "category": category,
        "count": len(filtered),
        "discrepancies": filtered,
        "total_financial_impact": sum(abs(d.get("financial_impact", 0)) for d in filtered),
    })
