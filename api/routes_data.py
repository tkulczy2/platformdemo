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
    """Return current data quality scores."""
    if state.data is None:
        return {
            "data_loaded": False,
            "quality_scores": [],
        }
    return {
        "data_loaded": True,
        "quality_scores": [serialize_quality_score(qs) for qs in state.quality_scores],
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
