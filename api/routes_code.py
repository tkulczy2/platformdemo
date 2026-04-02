"""Code introspection route — return source code of engine functions."""

import importlib
import inspect

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/code", tags=["code"])

# Allowed engine modules for introspection
ALLOWED_MODULES = {
    "pipeline": "engine.pipeline",
    "provenance": "engine.provenance",
    "data_loader": "engine.data_loader",
    "data_quality": "engine.data_quality",
    "step_1_eligibility": "engine.step_1_eligibility",
    "step_2_attribution": "engine.step_2_attribution",
    "step_3_quality": "engine.step_3_quality",
    "step_4_cost": "engine.step_4_cost",
    "step_5_settlement": "engine.step_5_settlement",
    "step_6_reconciliation": "engine.step_6_reconciliation",
    "measures.base": "engine.measures.base",
    "measures.hba1c_control": "engine.measures.hba1c_control",
    "measures.blood_pressure": "engine.measures.blood_pressure",
    "measures.breast_cancer_screening": "engine.measures.breast_cancer_screening",
    "measures.colorectal_screening": "engine.measures.colorectal_screening",
    "measures.depression_screening": "engine.measures.depression_screening",
}


@router.get("/{module}/{function}")
def get_source_code(module: str, function: str):
    """Return source code of a calculation function from the engine."""
    module_path = ALLOWED_MODULES.get(module)
    if module_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module}' not found. Available: {list(ALLOWED_MODULES.keys())}",
        )

    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Failed to import module: {e}")

    obj = getattr(mod, function, None)
    if obj is None:
        # List available functions/classes
        available = [
            name for name, _ in inspect.getmembers(mod, predicate=lambda m: inspect.isfunction(m) or inspect.isclass(m))
            if not name.startswith("_")
        ]
        raise HTTPException(
            status_code=404,
            detail=f"Function '{function}' not found in '{module}'. Available: {available}",
        )

    try:
        source = inspect.getsource(obj)
        source_file = inspect.getfile(obj)
        lines, start_line = inspect.getsourcelines(obj)
        end_line = start_line + len(lines) - 1
    except (OSError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve source: {e}")

    return {
        "module": module_path,
        "function": function,
        "source_file": source_file,
        "line_range": [start_line, end_line],
        "source_code": source,
        # Frontend-expected field names
        "source": source,
        "start_line": start_line,
        "end_line": end_line,
    }
