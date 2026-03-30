"""Data quality scoring — completeness and issue detection per file."""

from dataclasses import dataclass

import pandas as pd

from engine.data_loader import LoadedData, SCHEMAS


@dataclass
class FileQualityScore:
    """Quality assessment for a single data file."""
    file_name: str
    row_count: int
    completeness_score: float  # 0-1, fraction of non-null required fields
    date_range: tuple[str, str] | None
    issues: list[dict]
    status: str  # "green", "yellow", "red"


def score_completeness(df: pd.DataFrame, required_columns: list[str]) -> float:
    """Calculate fraction of non-null values across required columns."""
    if df.empty or not required_columns:
        return 0.0
    present = [c for c in required_columns if c in df.columns]
    if not present:
        return 0.0
    total_cells = len(df) * len(present)
    filled_cells = sum(df[c].notna().sum() for c in present)
    return filled_cells / total_cells


def _detect_date_range(df: pd.DataFrame, date_cols: list[str]) -> tuple[str, str] | None:
    """Find the min/max date across date columns."""
    dates = []
    for col in date_cols:
        if col in df.columns:
            valid = df[col].dropna()
            if not valid.empty:
                dates.extend([valid.min(), valid.max()])
    if not dates:
        return None
    return str(min(dates).date()), str(max(dates).date())


def _check_claims_issues(df: pd.DataFrame, file_name: str) -> list[dict]:
    """Check for common claims data issues."""
    issues = []

    if "rendering_npi" in df.columns:
        missing_npi = df["rendering_npi"].isna().sum()
        if missing_npi > 0:
            issues.append({
                "type": "missing_field",
                "field": "rendering_npi",
                "count": int(missing_npi),
                "severity": "yellow",
                "description": f"{missing_npi} claims missing rendering NPI",
            })

    if "claim_id" in df.columns:
        dupes = df["claim_id"].duplicated().sum()
        if dupes > 0:
            issues.append({
                "type": "duplicate",
                "field": "claim_id",
                "count": int(dupes),
                "severity": "yellow",
                "description": f"{dupes} duplicate claim IDs detected",
            })

    if "allowed_amount" in df.columns:
        invalid = (df["allowed_amount"].fillna(0) <= 0).sum()
        if invalid > 0:
            issues.append({
                "type": "invalid_value",
                "field": "allowed_amount",
                "count": int(invalid),
                "severity": "yellow",
                "description": f"{invalid} claims with zero or negative allowed amount",
            })

    if "claim_status" in df.columns:
        denied = (df["claim_status"] == "denied").sum()
        if denied > 0:
            issues.append({
                "type": "info",
                "field": "claim_status",
                "count": int(denied),
                "severity": "info",
                "description": f"{denied} denied claims (will be excluded from cost calculations)",
            })

    return issues


def assess_file(df: pd.DataFrame, schema_key: str, file_name: str) -> FileQualityScore:
    """Assess quality of a single data file."""
    schema = SCHEMAS[schema_key]
    required = schema["required"]
    date_cols = schema["date_columns"]

    completeness = score_completeness(df, required)
    date_range = _detect_date_range(df, date_cols)

    issues = []

    # Check missing required columns
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        issues.append({
            "type": "missing_column",
            "field": ", ".join(missing_cols),
            "count": len(missing_cols),
            "severity": "red",
            "description": f"Missing required columns: {', '.join(missing_cols)}",
        })

    # Claims-specific checks
    if "claim" in schema_key:
        issues.extend(_check_claims_issues(df, file_name))

    # Determine status
    if any(i["severity"] == "red" for i in issues):
        status = "red"
    elif completeness < 0.95 or any(i["severity"] == "yellow" for i in issues):
        status = "yellow"
    else:
        status = "green"

    return FileQualityScore(
        file_name=file_name,
        row_count=len(df),
        completeness_score=round(completeness, 4),
        date_range=date_range,
        issues=issues,
        status=status,
    )


def assess_all(data: LoadedData) -> list[FileQualityScore]:
    """Assess quality of all loaded data files."""
    assessments = [
        assess_file(data.members, "members", "members.csv"),
        assess_file(data.providers, "providers", "providers.csv"),
        assess_file(data.eligibility, "eligibility", "eligibility.csv"),
        assess_file(data.claims_professional, "claims_professional", "claims_professional.csv"),
        assess_file(data.claims_facility, "claims_facility", "claims_facility.csv"),
        assess_file(data.claims_pharmacy, "claims_pharmacy", "claims_pharmacy.csv"),
        assess_file(data.clinical_labs, "clinical_labs", "clinical_labs.csv"),
        assess_file(data.clinical_screenings, "clinical_screenings", "clinical_screenings.csv"),
        assess_file(data.clinical_vitals, "clinical_vitals", "clinical_vitals.csv"),
    ]
    return assessments
