"""Contract configuration routes."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.main import state

router = APIRouter(prefix="/api/contract", tags=["contract"])

CONTRACT_FILE = Path(__file__).parent.parent / "data" / "contracts" / "sample_mssp_contract.json"


@router.get("/")
def get_contract():
    """Return current contract configuration."""
    if state.contract is None:
        return {"contract_loaded": False, "contract": None}
    return {"contract_loaded": True, "contract": state.contract}


@router.put("/")
def update_contract(params: dict):
    """Update contract parameters. Merges into current contract."""
    if state.contract is None:
        state.contract = {}

    state.contract.update(params)
    # Clear stale results when contract changes
    state.pipeline_result = None

    return {
        "status": "success",
        "message": "Contract parameters updated",
        "contract": state.contract,
    }


@router.post("/load-demo")
def load_demo_contract():
    """Load the sample MSSP contract configuration."""
    if not CONTRACT_FILE.exists():
        raise HTTPException(status_code=500, detail="Sample contract file not found")

    with open(CONTRACT_FILE) as f:
        state.contract = json.load(f)

    # Clear stale results
    state.pipeline_result = None

    return {
        "status": "success",
        "message": "Sample MSSP contract loaded",
        "contract": state.contract,
    }
