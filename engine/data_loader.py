"""Load CSV data into pandas DataFrames with date parsing and schema validation."""

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).parent.parent / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
UPLOADS_DIR = DATA_DIR / "uploads"

# Expected schemas: column name -> required flag
SCHEMAS = {
    "members": {
        "required": ["member_id", "date_of_birth", "sex", "zip_code", "dual_eligible", "hcc_risk_score"],
        "date_columns": ["date_of_birth", "deceased_date"],
    },
    "providers": {
        "required": ["npi", "provider_name", "specialty", "is_pcp", "tin", "aco_participant"],
        "date_columns": ["effective_date", "termination_date"],
    },
    "eligibility": {
        "required": ["member_id", "payer_id", "contract_id", "product_type", "enrollment_start_date"],
        "date_columns": ["enrollment_start_date", "enrollment_end_date"],
    },
    "claims_professional": {
        "required": ["claim_id", "member_id", "service_date", "procedure_code", "allowed_amount", "paid_amount", "claim_status"],
        "date_columns": ["service_date", "adjudication_date"],
    },
    "claims_facility": {
        "required": ["claim_id", "member_id", "service_date", "allowed_amount", "paid_amount", "claim_status"],
        "date_columns": ["service_date", "admission_date", "discharge_date", "adjudication_date"],
    },
    "claims_pharmacy": {
        "required": ["claim_id", "member_id", "fill_date", "ndc_code", "drug_name", "allowed_amount", "paid_amount"],
        "date_columns": ["fill_date"],
    },
    "clinical_labs": {
        "required": ["member_id", "lab_date", "loinc_code", "lab_name", "result_value"],
        "date_columns": ["lab_date"],
    },
    "clinical_screenings": {
        "required": ["member_id", "screening_date", "screening_type"],
        "date_columns": ["screening_date"],
    },
    "clinical_vitals": {
        "required": ["member_id", "vital_date", "vital_type", "value"],
        "date_columns": ["vital_date"],
    },
}


@dataclass
class LoadedData:
    """Container for all loaded DataFrames."""
    members: pd.DataFrame
    providers: pd.DataFrame
    eligibility: pd.DataFrame
    claims_professional: pd.DataFrame
    claims_facility: pd.DataFrame
    claims_pharmacy: pd.DataFrame
    clinical_labs: pd.DataFrame
    clinical_screenings: pd.DataFrame
    clinical_vitals: pd.DataFrame


def _load_csv(filepath: Path, schema_key: str) -> pd.DataFrame:
    """Load a CSV file, parse dates, and validate required columns."""
    schema = SCHEMAS[schema_key]
    df = pd.read_csv(filepath, dtype=str)

    # Check required columns
    missing = [c for c in schema["required"] if c not in df.columns]
    if missing:
        raise ValueError(f"{filepath.name}: missing required columns: {missing}")

    # Parse date columns
    for col in schema["date_columns"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Parse numeric columns
    numeric_cols = ["allowed_amount", "paid_amount", "patient_responsibility",
                    "hcc_risk_score", "result_value", "value", "quantity", "days_supply"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse boolean columns
    bool_cols = ["dual_eligible", "is_pcp", "aco_participant", "attribution_eligible"]
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].map({"True": True, "False": False, "true": True, "false": False})

    return df


def load_demo_data() -> LoadedData:
    """Load all synthetic demo data files."""
    return load_from_directory(SYNTHETIC_DIR)


def load_from_directory(directory: Path) -> LoadedData:
    """Load all data files from a directory."""
    directory = Path(directory)
    files = {
        "members": "members.csv",
        "providers": "providers.csv",
        "eligibility": "eligibility.csv",
        "claims_professional": "claims_professional.csv",
        "claims_facility": "claims_facility.csv",
        "claims_pharmacy": "claims_pharmacy.csv",
        "clinical_labs": "clinical_labs.csv",
        "clinical_screenings": "clinical_screenings.csv",
        "clinical_vitals": "clinical_vitals.csv",
    }

    frames = {}
    for key, filename in files.items():
        filepath = directory / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Required file not found: {filepath}")
        frames[key] = _load_csv(filepath, key)

    return LoadedData(**frames)
