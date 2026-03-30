"""FastAPI application for the VBC Transparent Calculation Demo Tool.

Thin API layer over the calculation engine. All state is held in-memory.
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.data_loader import LoadedData
from engine.data_quality import FileQualityScore
from engine.provenance import PipelineResult


@dataclass
class AppState:
    """In-memory application state. No database."""
    data: LoadedData | None = None
    contract: dict | None = None
    pipeline_result: PipelineResult | None = None
    quality_scores: list[FileQualityScore] = field(default_factory=list)
    payer_report: dict | None = None


# Module-level state instance, imported by route modules
state = AppState()


def serialize_dataclass(obj: Any) -> Any:
    """Recursively convert dataclasses to dicts, handling special types."""
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for k, v in asdict(obj).items():
            d[k] = _fix_values(v)
        return d
    return obj


def _fix_values(v: Any) -> Any:
    """Fix values that don't serialize cleanly to JSON."""
    if isinstance(v, tuple):
        return list(v)
    if isinstance(v, dict):
        return {k: _fix_values(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_fix_values(item) for item in v]
    return v


def serialize_quality_score(qs: FileQualityScore) -> dict:
    """Serialize a FileQualityScore to a JSON-friendly dict."""
    return {
        "file_name": qs.file_name,
        "row_count": qs.row_count,
        "completeness_score": qs.completeness_score,
        "date_range": list(qs.date_range) if qs.date_range else None,
        "issues": qs.issues,
        "status": qs.status,
    }


def serialize_step_result(step) -> dict:
    """Serialize a StepResult to a JSON-friendly dict."""
    return _fix_values(asdict(step))


def serialize_pipeline_result(result: PipelineResult) -> dict:
    """Serialize a PipelineResult to a JSON-friendly dict."""
    return _fix_values(asdict(result))


# Build the FastAPI app
app = FastAPI(
    title="VBC Transparent Calculation Demo",
    description="Transparent value-based care performance calculation with full provenance",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from api.routes_data import router as data_router
from api.routes_contract import router as contract_router
from api.routes_calculate import router as calculate_router
from api.routes_drilldown import router as drilldown_router
from api.routes_reconciliation import router as reconciliation_router
from api.routes_code import router as code_router

app.include_router(data_router)
app.include_router(contract_router)
app.include_router(calculate_router)
app.include_router(drilldown_router)
app.include_router(reconciliation_router)
app.include_router(code_router)


@app.get("/")
def root():
    return {
        "name": "VBC Transparent Calculation Demo",
        "version": "1.0.0",
        "status": "running",
        "data_loaded": state.data is not None,
        "contract_loaded": state.contract is not None,
        "pipeline_run": state.pipeline_result is not None,
    }
