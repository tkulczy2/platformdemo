"""Data upload and validation routes."""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from engine.data_loader import load_demo_data, load_from_directory, UPLOADS_DIR
from engine.data_quality import assess_all

from api.main import state, serialize_quality_score

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/upload")
async def upload_data(files: list[UploadFile] = File(...)):
    """Accept uploaded CSV files, save to uploads dir, load and validate."""
    # Ensure uploads directory exists
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for upload_file in files:
        if not upload_file.filename:
            continue
        dest = UPLOADS_DIR / upload_file.filename
        with open(dest, "wb") as f:
            content = await upload_file.read()
            f.write(content)
        saved_files.append(upload_file.filename)

    if not saved_files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    try:
        state.data = load_from_directory(UPLOADS_DIR)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    state.quality_scores = assess_all(state.data)
    # Clear stale results when new data is loaded
    state.pipeline_result = None

    return {
        "status": "success",
        "files_uploaded": saved_files,
        "quality_scores": [serialize_quality_score(qs) for qs in state.quality_scores],
    }


@router.get("/status")
def data_status():
    """Return current data quality scores.

    Returns the shape the frontend expects:
      { files: Record<filename, ...>, overall_quality: float, ready: bool }
    """
    if state.data is None:
        return {
            "files": {},
            "overall_quality": 0,
            "ready": False,
        }

    files: dict = {}
    for qs in state.quality_scores:
        # Serialize issues as human-readable strings for the frontend
        issue_strings = [
            issue["description"] if isinstance(issue, dict) else str(issue)
            for issue in qs.issues
        ]
        files[qs.file_name] = {
            "file_name": qs.file_name,
            "rows": qs.row_count,
            "completeness": qs.completeness_score,
            "quality_score": qs.completeness_score,
            "date_range": list(qs.date_range) if qs.date_range else None,
            "issues": issue_strings,
            "status": qs.status,
        }

    scores = [qs.completeness_score for qs in state.quality_scores]
    overall = sum(scores) / len(scores) if scores else 0
    # Ready when all 9 files are loaded and none are red
    ready = (
        len(state.quality_scores) >= 9
        and all(qs.status != "red" for qs in state.quality_scores)
    )

    return {
        "files": files,
        "overall_quality": round(overall, 4),
        "ready": ready,
    }


@router.post("/load-demo")
def load_demo():
    """Load synthetic demo data and return quality scores."""
    try:
        state.data = load_demo_data()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to load demo data: {e}")

    state.quality_scores = assess_all(state.data)
    # Clear stale results
    state.pipeline_result = None

    return {
        "status": "success",
        "message": "Demo data loaded successfully",
        "quality_scores": [serialize_quality_score(qs) for qs in state.quality_scores],
    }
