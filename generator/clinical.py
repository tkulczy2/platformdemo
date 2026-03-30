"""Generate EHR-sourced clinical data: lab results, screenings, vitals.

This data may intentionally conflict with claims data in some cases — EHR/claims
discrepancies are a key demo feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.config import GenerationConfig

# ---------------------------------------------------------------------------
# LOINC codes for labs
# ---------------------------------------------------------------------------
LAB_SPECS = {
    "hba1c": {
        "loinc": "4548-4",
        "lab_name": "Hemoglobin A1c",
        "unit": "%",
        "reference_range": "4.0-5.6",
    },
    "ldl": {
        "loinc": "2089-1",
        "lab_name": "LDL Cholesterol",
        "unit": "mg/dL",
        "reference_range": "<100",
    },
    "egfr": {
        "loinc": "33914-3",
        "lab_name": "Estimated GFR",
        "unit": "mL/min/1.73m2",
        "reference_range": ">60",
    },
    "creatinine": {
        "loinc": "2160-0",
        "lab_name": "Creatinine",
        "unit": "mg/dL",
        "reference_range": "0.7-1.3",
    },
}


def _is_diabetic(member: pd.Series) -> bool:
    """Heuristic: 15% of population has diabetes, correlated with risk score."""
    # Members with higher risk scores are more likely diabetic.
    # We use member_id hash + risk score to create a deterministic flag.
    member_hash = hash(member["member_id"]) % 1000
    threshold = 150 + int(member["hcc_risk_score"] * 50)
    return member_hash < threshold


def _is_hypertensive(member: pd.Series) -> bool:
    """Heuristic: ~40% of Medicare population has hypertension."""
    member_hash = hash(member["member_id"]) % 1000
    threshold = 400 + int(member["hcc_risk_score"] * 30)
    return member_hash < min(threshold, 700)


def generate_clinical_labs(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate lab results from EHR data."""
    rng = np.random.default_rng(config.seed + 5)

    pcp_npis = providers_df[providers_df["is_pcp"] == True]["npi"].tolist()
    perf_year = config.performance_year

    rows: list[dict] = []

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        ordering_npi = member["pcp_npi"]

        # All members get 1-2 routine labs per year (CMP, lipid)
        num_routine = int(rng.integers(1, 3))
        for _ in range(num_routine):
            lab_month = int(rng.integers(1, 11))
            lab_date = f"{perf_year}-{lab_month:02d}-{int(rng.integers(1, 29)):02d}"

            # LDL
            ldl_value = round(float(rng.normal(120, 35)), 1)
            rows.append({
                "member_id": member_id,
                "lab_date": lab_date,
                "loinc_code": LAB_SPECS["ldl"]["loinc"],
                "lab_name": LAB_SPECS["ldl"]["lab_name"],
                "result_value": ldl_value,
                "result_unit": LAB_SPECS["ldl"]["unit"],
                "reference_range": LAB_SPECS["ldl"]["reference_range"],
                "abnormal_flag": "H" if ldl_value >= 100 else None,
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

            # Creatinine
            creat_value = round(float(rng.normal(1.0, 0.3)), 2)
            creat_value = max(0.3, creat_value)
            rows.append({
                "member_id": member_id,
                "lab_date": lab_date,
                "loinc_code": LAB_SPECS["creatinine"]["loinc"],
                "lab_name": LAB_SPECS["creatinine"]["lab_name"],
                "result_value": creat_value,
                "result_unit": LAB_SPECS["creatinine"]["unit"],
                "reference_range": LAB_SPECS["creatinine"]["reference_range"],
                "abnormal_flag": "H" if creat_value > 1.3 else None,
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

        # Diabetic members: 1-3 HbA1c results per year
        if _is_diabetic(member):
            num_a1c = int(rng.integers(1, 4))
            for j in range(num_a1c):
                lab_month = int(rng.integers(1, 11))
                lab_date = f"{perf_year}-{lab_month:02d}-{int(rng.integers(1, 29)):02d}"

                # Distribution: 60% < 8 (controlled), 25% 8-9, 15% > 9 (poor)
                roll = rng.random()
                if roll < 0.60:
                    a1c = round(float(rng.uniform(5.5, 7.9)), 1)
                elif roll < 0.85:
                    a1c = round(float(rng.uniform(8.0, 9.0)), 1)
                else:
                    a1c = round(float(rng.uniform(9.1, 13.0)), 1)

                abnormal = "H" if a1c > 5.6 else None
                rows.append({
                    "member_id": member_id,
                    "lab_date": lab_date,
                    "loinc_code": LAB_SPECS["hba1c"]["loinc"],
                    "lab_name": LAB_SPECS["hba1c"]["lab_name"],
                    "result_value": a1c,
                    "result_unit": LAB_SPECS["hba1c"]["unit"],
                    "reference_range": LAB_SPECS["hba1c"]["reference_range"],
                    "abnormal_flag": abnormal,
                    "ordering_npi": ordering_npi,
                    "data_source": "ehr",
                })

            # eGFR for diabetics
            egfr_value = round(float(rng.normal(75, 25)), 1)
            egfr_value = max(5, egfr_value)
            lab_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            rows.append({
                "member_id": member_id,
                "lab_date": lab_date,
                "loinc_code": LAB_SPECS["egfr"]["loinc"],
                "lab_name": LAB_SPECS["egfr"]["lab_name"],
                "result_value": egfr_value,
                "result_unit": LAB_SPECS["egfr"]["unit"],
                "reference_range": LAB_SPECS["egfr"]["reference_range"],
                "abnormal_flag": "L" if egfr_value < 60 else None,
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

    return pd.DataFrame(rows)


def generate_clinical_screenings(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate screening records from EHR."""
    rng = np.random.default_rng(config.seed + 6)

    perf_year = config.performance_year
    rows: list[dict] = []

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        age = member["age"]
        sex = member["sex"]
        ordering_npi = member["pcp_npi"]

        # Colorectal screening: age 45-75, ~65% completion
        if 45 <= age <= 75 and rng.random() < 0.65:
            scr_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            rows.append({
                "member_id": member_id,
                "screening_date": scr_date,
                "screening_type": "colonoscopy",
                "cpt_code": "45378",
                "result": "normal" if rng.random() < 0.85 else "polyp_found",
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

        # Breast cancer screening: female age 50-74, ~70% completion
        if sex == "F" and 50 <= age <= 74 and rng.random() < 0.70:
            scr_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            rows.append({
                "member_id": member_id,
                "screening_date": scr_date,
                "screening_type": "mammogram",
                "cpt_code": "77067",
                "result": "normal" if rng.random() < 0.90 else "abnormal_callback",
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

        # Depression screening: all adults, ~55% completion
        if age >= 18 and rng.random() < 0.55:
            scr_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            phq9_score = int(rng.integers(0, 28))
            result = "negative" if phq9_score < 10 else "positive"
            rows.append({
                "member_id": member_id,
                "screening_date": scr_date,
                "screening_type": "depression_screening",
                "cpt_code": "96127",
                "result": result,
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

        # Tobacco screening: ~40% of members
        if rng.random() < 0.40:
            scr_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            rows.append({
                "member_id": member_id,
                "screening_date": scr_date,
                "screening_type": "tobacco_screening",
                "cpt_code": "99406",
                "result": "current_smoker" if rng.random() < 0.15 else "non_smoker",
                "ordering_npi": ordering_npi,
                "data_source": "ehr",
            })

    return pd.DataFrame(rows)


def generate_clinical_vitals(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate vital sign records from EHR."""
    rng = np.random.default_rng(config.seed + 7)

    perf_year = config.performance_year
    rows: list[dict] = []

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        provider_npi = member["pcp_npi"]

        # All members get 1-2 BMI/weight readings
        num_vitals = int(rng.integers(1, 3))
        for _ in range(num_vitals):
            vital_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"
            bmi = round(float(rng.normal(28, 6)), 1)
            bmi = max(16, min(55, bmi))

            rows.append({
                "member_id": member_id,
                "vital_date": vital_date,
                "vital_type": "bmi",
                "value": bmi,
                "unit": "kg/m2",
                "provider_npi": provider_npi,
                "data_source": "ehr",
            })

            weight = round(bmi * rng.uniform(1.8, 2.2) * rng.uniform(0.9, 1.1), 1)
            rows.append({
                "member_id": member_id,
                "vital_date": vital_date,
                "vital_type": "weight",
                "value": round(weight, 1),
                "unit": "kg",
                "provider_npi": provider_npi,
                "data_source": "ehr",
            })

        # Hypertensive members: 2-4 BP readings per year
        if _is_hypertensive(member):
            num_bp = int(rng.integers(2, 5))
            for _ in range(num_bp):
                vital_date = f"{perf_year}-{int(rng.integers(1, 11)):02d}-{int(rng.integers(1, 29)):02d}"

                # 65% controlled (< 140/90), 35% uncontrolled
                if rng.random() < 0.65:
                    systolic = round(float(rng.normal(128, 8)), 0)
                    diastolic = round(float(rng.normal(78, 5)), 0)
                else:
                    systolic = round(float(rng.normal(155, 12)), 0)
                    diastolic = round(float(rng.normal(95, 8)), 0)

                systolic = max(90, min(220, systolic))
                diastolic = max(50, min(130, diastolic))

                rows.append({
                    "member_id": member_id,
                    "vital_date": vital_date,
                    "vital_type": "systolic_bp",
                    "value": systolic,
                    "unit": "mmHg",
                    "provider_npi": provider_npi,
                    "data_source": "ehr",
                })
                rows.append({
                    "member_id": member_id,
                    "vital_date": vital_date,
                    "vital_type": "diastolic_bp",
                    "value": diastolic,
                    "unit": "mmHg",
                    "provider_npi": provider_npi,
                    "data_source": "ehr",
                })

    return pd.DataFrame(rows)
