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


def serialize_contract_clause(clause) -> dict:
    """Serialize a ContractClause for the frontend (uses id/text field names)."""
    return {
        "id": clause.clause_id,
        "text": clause.clause_text,
        "section": clause.interpretation,
        "title": clause.clause_id,
        "parameters": _fix_values(clause.parameters_extracted),
    }


def serialize_code_reference(ref) -> dict:
    """Serialize a CodeReference for the frontend."""
    start, end = ref.line_range if isinstance(ref.line_range, (tuple, list)) else (0, 0)
    return {
        "module": ref.module,
        "function": ref.function,
        "lines": f"{start}-{end}",
        "start_line": start,
        "end_line": end,
        "logic_summary": ref.logic_summary,
    }


def serialize_data_reference(ref) -> dict:
    """Serialize a DataReference for the frontend (flattens row_indices)."""
    return {
        "file": ref.source_file,
        "row_indices": ref.row_indices,
        "columns_used": ref.columns_used,
        "description": ref.description,
    }


def serialize_member_detail(detail) -> dict:
    """Serialize a MemberDetail for the frontend."""
    # Build per-row data references with column values as placeholder keys
    data_refs = []
    for dr in detail.data_references:
        for row_idx in dr.row_indices:
            cols = {c: None for c in dr.columns_used}
            data_refs.append({
                "file": dr.source_file,
                "row_index": row_idx,
                "columns": cols,
                "description": dr.description,
            })

    # Convert intermediate_values dict to list of {label, value}
    iv_list = [
        {"label": k, "value": _fix_values(v)}
        for k, v in (detail.intermediate_values or {}).items()
    ]

    return {
        "member_id": detail.member_id,
        "outcome": detail.outcome,
        "reason": detail.reason,
        "data_references": data_refs,
        "intermediate_values": iv_list,
    }


def serialize_step_result(step) -> dict:
    """Serialize a StepResult for the frontend with consistent field names."""
    return {
        "step_number": step.step_number,
        "step_name": step.step_name,
        "step": step.step_number,
        "name": step.step_name,
        "contract_clauses": [serialize_contract_clause(c) for c in step.contract_clauses],
        "code_references": [serialize_code_reference(r) for r in step.code_references],
        "logic_summary": step.code_references[0].logic_summary if step.code_references else "",
        "summary": _fix_values(step.summary),
        "member_count": len(step.member_details),
        "member_details": [serialize_member_detail(m) for m in step.member_details],
        "data_quality_flags": _fix_values(step.data_quality_flags),
        "execution_time_ms": step.execution_time_ms,
    }


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
from api.routes_export import router as export_router

app.include_router(data_router)
app.include_router(contract_router)
app.include_router(calculate_router)
app.include_router(drilldown_router)
app.include_router(reconciliation_router)
app.include_router(code_router)
app.include_router(export_router)


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
