"""Generate professional, facility, and pharmacy claims.

Professional claims are the largest dataset (~45-55K rows) and drive attribution
via E&M visit codes.  Facility and pharmacy claims are smaller but feed cost and
quality calculations.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.config import GenerationConfig

# ---------------------------------------------------------------------------
# CPT code pools
# ---------------------------------------------------------------------------

# E&M office visits (drive attribution)
EM_CODES = [
    ("99211", "Office visit, est. patient, minimal"),
    ("99212", "Office visit, est. patient, straightforward"),
    ("99213", "Office visit, est. patient, low complexity"),
    ("99214", "Office visit, est. patient, moderate complexity"),
    ("99215", "Office visit, est. patient, high complexity"),
    ("99202", "Office visit, new patient, straightforward"),
    ("99203", "Office visit, new patient, low complexity"),
    ("99204", "Office visit, new patient, moderate complexity"),
    ("99205", "Office visit, new patient, high complexity"),
]

# Wellness visits
WELLNESS_CODES = [
    ("99381", "Preventive visit, new patient, infant"),
    ("99385", "Preventive visit, new patient, 18-39"),
    ("99386", "Preventive visit, new patient, 40-64"),
    ("99387", "Preventive visit, new patient, 65+"),
    ("99391", "Preventive visit, est. patient, infant"),
    ("99395", "Preventive visit, est. patient, 18-39"),
    ("99396", "Preventive visit, est. patient, 40-64"),
    ("99397", "Preventive visit, est. patient, 65+"),
    ("G0438", "Annual wellness visit, initial"),
    ("G0439", "Annual wellness visit, subsequent"),
]

# Lab procedure codes
LAB_CODES = [
    ("80053", "Comprehensive metabolic panel"),
    ("80061", "Lipid panel"),
    ("83036", "Hemoglobin A1c"),
    ("85025", "CBC with differential"),
    ("81001", "Urinalysis"),
    ("84443", "Thyroid stimulating hormone"),
    ("82947", "Glucose, quantitative"),
    ("82306", "Vitamin D, 25-OH"),
]

# Specialist procedure codes by specialty
SPECIALIST_CODES: dict[str, list[tuple[str, str]]] = {
    "Cardiology": [
        ("93000", "Electrocardiogram, 12-lead"),
        ("93306", "Echocardiography, transthoracic"),
        ("93458", "Left heart catheterization"),
        ("99214", "Office visit, moderate complexity"),
    ],
    "Endocrinology": [
        ("99214", "Office visit, moderate complexity"),
        ("83036", "Hemoglobin A1c"),
        ("84443", "Thyroid stimulating hormone"),
        ("76942", "Ultrasound-guided biopsy, thyroid"),
    ],
    "Orthopedics": [
        ("99213", "Office visit, low complexity"),
        ("73721", "MRI, knee"),
        ("27447", "Total knee arthroplasty"),
        ("20610", "Joint injection, major"),
    ],
    "Pulmonology": [
        ("99214", "Office visit, moderate complexity"),
        ("94010", "Spirometry"),
        ("94060", "Bronchospasm evaluation"),
        ("71046", "Chest X-ray, 2 views"),
    ],
    "General Surgery": [
        ("99213", "Office visit, low complexity"),
        ("47562", "Laparoscopic cholecystectomy"),
        ("49505", "Inguinal hernia repair"),
        ("43239", "Upper GI endoscopy with biopsy"),
    ],
    "Nephrology": [
        ("99214", "Office visit, moderate complexity"),
        ("90935", "Hemodialysis, single evaluation"),
        ("82565", "Creatinine, blood"),
        ("82575", "Creatinine clearance test"),
    ],
    "Neurology": [
        ("99214", "Office visit, moderate complexity"),
        ("95819", "EEG with sleep"),
        ("70553", "Brain MRI with/without contrast"),
        ("95910", "Nerve conduction, 7-8 studies"),
    ],
    "Psychiatry": [
        ("99213", "Office visit, low complexity"),
        ("90834", "Psychotherapy, 45 min"),
        ("90837", "Psychotherapy, 60 min"),
        ("96127", "Depression screening (PHQ-9)"),
    ],
}

# Screening CPT codes (feed quality measures)
SCREENING_CODES = {
    "mammogram": ("77067", "Screening mammography, bilateral"),
    "colonoscopy": ("45378", "Colonoscopy, diagnostic"),
    "depression_phq9": ("96127", "Depression screening (PHQ-9)"),
    "tobacco_screening": ("99406", "Tobacco use counseling, 3-10 min"),
}

# Common ICD-10 diagnosis codes
DIAGNOSIS_POOL = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential hypertension"),
    ("E78.5", "Hyperlipidemia, unspecified"),
    ("J06.9", "Acute upper respiratory infection"),
    ("M79.3", "Panniculitis, unspecified"),
    ("R10.9", "Unspecified abdominal pain"),
    ("Z00.00", "Encounter for general adult medical examination"),
    ("J44.1", "COPD with acute exacerbation"),
    ("M54.5", "Low back pain"),
    ("G47.00", "Insomnia, unspecified"),
    ("F32.9", "Major depressive disorder, single episode"),
    ("K21.0", "GERD with esophagitis"),
    ("N18.6", "End stage renal disease"),
    ("Z87.891", "Personal history of nicotine dependence"),
]

# Place of service codes
POS_CODES = {
    "office": "11",
    "inpatient": "21",
    "ed": "23",
    "outpatient": "22",
    "home": "12",
}

# Claims run-out maturity curve: fraction of claims received by months-since-service
RUNOUT_CURVE = {
    0: 0.40,
    1: 0.82,
    2: 0.92,
    3: 0.96,
    4: 0.98,
    5: 0.99,
    6: 0.995,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enrollment_months(
    member_id: str,
    eligibility_df: pd.DataFrame,
    perf_start: pd.Timestamp,
    perf_end: pd.Timestamp,
) -> list[int]:
    """Return list of months (1-12) the member is enrolled during the perf year."""
    member_elig = eligibility_df[eligibility_df["member_id"] == member_id]
    enrolled_months: set[int] = set()

    for _, erow in member_elig.iterrows():
        start = pd.Timestamp(erow["enrollment_start_date"])
        end_raw = erow.get("enrollment_end_date")
        end = pd.Timestamp(end_raw) if pd.notna(end_raw) and end_raw else perf_end
        # Clip to performance year
        start = max(start, perf_start)
        end = min(end, perf_end)
        if start > end:
            continue
        for m in range(start.month, end.month + 1):
            enrolled_months.add(m)

    return sorted(enrolled_months)


def _should_generate_claim(
    rng: np.random.Generator,
    service_month: int,
    data_as_of: pd.Timestamp,
    perf_year: int,
) -> bool:
    """Apply claims run-out curve: recent months have fewer claims in the data."""
    service_date_approx = pd.Timestamp(year=perf_year, month=service_month, day=15)
    months_elapsed = (data_as_of.year - service_date_approx.year) * 12 + (
        data_as_of.month - service_date_approx.month
    )
    months_elapsed = max(0, months_elapsed)
    # Find maturity fraction
    maturity = 1.0
    for lag, frac in sorted(RUNOUT_CURVE.items(), reverse=True):
        if months_elapsed >= lag:
            maturity = frac
            break
    else:
        maturity = RUNOUT_CURVE[0]
    return float(rng.random()) < maturity


def _random_date_in_month(
    rng: np.random.Generator, year: int, month: int,
) -> str:
    """Return a random YYYY-MM-DD within the given month."""
    day = int(rng.integers(1, 29))  # safe for all months
    return f"{year:04d}-{month:02d}-{day:02d}"


def _claim_amounts(rng: np.random.Generator, code: str) -> tuple[float, float, float]:
    """Return (allowed_amount, paid_amount, patient_responsibility)."""
    # Base amount depends roughly on code type
    if code.startswith("992"):
        base = rng.uniform(75, 250)
    elif code.startswith("G0"):
        base = rng.uniform(150, 350)
    elif code.startswith(("8", "7")):  # labs, imaging
        base = rng.uniform(30, 500)
    elif code.startswith(("4", "2")):  # procedures/surgeries
        base = rng.uniform(500, 5000)
    elif code.startswith("9"):  # other professional services
        base = rng.uniform(50, 300)
    else:
        base = rng.uniform(50, 200)

    allowed = round(base, 2)
    patient_pct = rng.uniform(0.0, 0.20)
    patient_resp = round(allowed * patient_pct, 2)
    paid = round(allowed - patient_resp, 2)
    return allowed, paid, patient_resp


# ---------------------------------------------------------------------------
# Professional claims
# ---------------------------------------------------------------------------

def generate_professional_claims(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate ~45,000-55,000 professional claims."""
    rng = np.random.default_rng(config.seed + 2)

    perf_start = pd.Timestamp(config.performance_period_start)
    perf_end = pd.Timestamp(config.performance_period_end)
    data_as_of = pd.Timestamp(config.data_as_of_date)

    pcp_npis = providers_df[providers_df["is_pcp"] == True]["npi"].tolist()
    specialist_rows = providers_df[providers_df["is_pcp"] == False]

    # Build specialty-to-NPI lookup
    specialty_npi_map: dict[str, list[str]] = {}
    for _, srow in specialist_rows.iterrows():
        sp = srow["specialty"]
        specialty_npi_map.setdefault(sp, []).append(srow["npi"])

    all_specialist_npis = specialist_rows["npi"].tolist()

    # Pre-compute enrollment months per member for efficiency
    elig_lookup: dict[str, list[int]] = {}
    for mid in members_df["member_id"]:
        elig_lookup[mid] = _enrollment_months(mid, eligibility_df, perf_start, perf_end)

    rows: list[dict] = []
    claim_counter = 0

    # Track edge-case members for multi-PCP visit distribution
    edge_case_ids = set(
        members_df[members_df["attribution_edge_case"] == True]["member_id"]
    )

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        pcp_npi = member["pcp_npi"]
        enrolled_months = elig_lookup.get(member_id, [])
        if not enrolled_months:
            continue

        is_edge_case = member_id in edge_case_ids
        risk = member["hcc_risk_score"]

        # Claims volume scales with risk score
        volume_multiplier = max(0.5, risk / 1.2)

        for month in enrolled_months:
            # Apply run-out curve
            num_claims_raw = rng.poisson(
                config.avg_professional_claims_pmpm * volume_multiplier
            )

            for _ in range(num_claims_raw):
                if not _should_generate_claim(rng, month, data_as_of, config.performance_year):
                    continue

                claim_counter += 1
                claim_id = f"CLM-P-{claim_counter:08d}"
                service_date = _random_date_in_month(rng, config.performance_year, month)

                # Decide claim type: 40% E&M, 15% wellness, 25% lab, 20% specialist
                claim_type_roll = rng.random()

                if claim_type_roll < 0.40:
                    # E&M visit — goes to PCP (or split across PCPs for edge cases)
                    code, desc = EM_CODES[int(rng.integers(0, len(EM_CODES)))]
                    if is_edge_case and rng.random() < 0.5:
                        # Edge case: send to a random OTHER PCP to create plurality conflict
                        alt_pcps = [p for p in pcp_npis if p != pcp_npi]
                        rendering_npi = rng.choice(alt_pcps) if alt_pcps else pcp_npi
                    else:
                        rendering_npi = pcp_npi
                    pos = POS_CODES["office"]
                    dx_code, dx_desc = DIAGNOSIS_POOL[int(rng.integers(0, len(DIAGNOSIS_POOL)))]

                elif claim_type_roll < 0.55:
                    # Wellness visit — goes to PCP
                    code, desc = WELLNESS_CODES[int(rng.integers(0, len(WELLNESS_CODES)))]
                    rendering_npi = pcp_npi
                    pos = POS_CODES["office"]
                    dx_code = "Z00.00"
                    dx_desc = "Encounter for general adult medical examination"

                elif claim_type_roll < 0.80:
                    # Lab order
                    code, desc = LAB_CODES[int(rng.integers(0, len(LAB_CODES)))]
                    rendering_npi = pcp_npi
                    pos = POS_CODES["office"]
                    dx_code, dx_desc = DIAGNOSIS_POOL[int(rng.integers(0, len(DIAGNOSIS_POOL)))]

                else:
                    # Specialist visit
                    specialty = rng.choice(list(specialty_npi_map.keys()))
                    spec_npis = specialty_npi_map[specialty]
                    rendering_npi = rng.choice(spec_npis)
                    spec_codes = SPECIALIST_CODES.get(specialty, EM_CODES)
                    code, desc = spec_codes[int(rng.integers(0, len(spec_codes)))]
                    pos = POS_CODES["office"]
                    dx_code, dx_desc = DIAGNOSIS_POOL[int(rng.integers(0, len(DIAGNOSIS_POOL)))]

                allowed, paid, patient_resp = _claim_amounts(rng, code)

                # Adjudication date: service date + 14-60 day lag
                svc_ts = pd.Timestamp(service_date)
                adj_lag = int(rng.integers(14, 61))
                adj_date = (svc_ts + pd.Timedelta(days=adj_lag)).strftime("%Y-%m-%d")

                # Secondary diagnoses (0-3 additional)
                num_extra_dx = int(rng.integers(0, 4))
                extra_dx_indices = rng.integers(0, len(DIAGNOSIS_POOL), size=num_extra_dx)
                dx2 = DIAGNOSIS_POOL[extra_dx_indices[0]][0] if num_extra_dx > 0 else None
                dx3 = DIAGNOSIS_POOL[extra_dx_indices[1]][0] if num_extra_dx > 1 else None
                dx4 = DIAGNOSIS_POOL[extra_dx_indices[2]][0] if num_extra_dx > 2 else None

                rows.append({
                    "claim_id": claim_id,
                    "member_id": member_id,
                    "service_date": service_date,
                    "rendering_npi": rendering_npi,
                    "billing_npi": rendering_npi,  # same for most claims
                    "place_of_service": pos,
                    "procedure_code": code,
                    "procedure_description": desc,
                    "modifier": None,
                    "diagnosis_code_1": dx_code,
                    "diagnosis_description_1": dx_desc,
                    "diagnosis_code_2": dx2,
                    "diagnosis_code_3": dx3,
                    "diagnosis_code_4": dx4,
                    "allowed_amount": allowed,
                    "paid_amount": paid,
                    "patient_responsibility": patient_resp,
                    "claim_status": "paid",
                    "adjudication_date": adj_date,
                    "data_source": "payer_claims_feed",
                })

    df = pd.DataFrame(rows)

    # -----------------------------------------------------------------------
    # Inject data quality issues
    # -----------------------------------------------------------------------
    n_claims = len(df)

    # 2% missing rendering NPI
    missing_npi_count = int(n_claims * config.pct_missing_npi)
    missing_npi_idx = rng.choice(n_claims, size=missing_npi_count, replace=False)
    df.loc[missing_npi_idx, "rendering_npi"] = None

    # 1% duplicate claims (exact duplicates)
    dup_count = int(n_claims * config.pct_duplicate_claims)
    dup_idx = rng.choice(n_claims, size=dup_count, replace=False)
    duplicates = df.iloc[dup_idx].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    # 0.5% denied claims
    denied_count = int(n_claims * 0.005)
    denied_idx = rng.choice(len(df), size=denied_count, replace=False)
    df.loc[denied_idx, "claim_status"] = "denied"
    df.loc[denied_idx, "paid_amount"] = 0.0

    # A few claims with $0 or negative allowed amounts
    zero_count = int(rng.integers(5, 15))
    zero_idx = rng.choice(len(df), size=zero_count, replace=False)
    df.loc[zero_idx[:zero_count // 2], "allowed_amount"] = 0.0
    df.loc[zero_idx[zero_count // 2:], "allowed_amount"] = -rng.uniform(10, 50, size=len(zero_idx[zero_count // 2:]))

    return df


# ---------------------------------------------------------------------------
# Facility claims
# ---------------------------------------------------------------------------

def generate_facility_claims(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate facility claims: inpatient, ED, outpatient facility."""
    rng = np.random.default_rng(config.seed + 3)

    perf_start = pd.Timestamp(config.performance_period_start)
    perf_end = pd.Timestamp(config.performance_period_end)
    data_as_of = pd.Timestamp(config.data_as_of_date)

    rows: list[dict] = []
    claim_counter = 0

    # Pre-compute enrollment months
    elig_lookup: dict[str, list[int]] = {}
    for mid in members_df["member_id"]:
        elig_lookup[mid] = _enrollment_months(mid, eligibility_df, perf_start, perf_end)

    facility_npis = providers_df[providers_df["is_pcp"] == False]["npi"].tolist()
    if not facility_npis:
        facility_npis = providers_df["npi"].tolist()

    # DRG codes for inpatient stays
    drg_codes = [
        ("470", "Major joint replacement"),
        ("291", "Heart failure"),
        ("065", "Intracranial hemorrhage"),
        ("194", "Simple pneumonia"),
        ("392", "Esophagitis/gastritis"),
        ("690", "Kidney/urinary tract infections"),
    ]

    revenue_codes = ["0120", "0250", "0260", "0301", "0320", "0450"]

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        enrolled_months = elig_lookup.get(member_id, [])
        if not enrolled_months:
            continue

        risk = member["hcc_risk_score"]
        volume_mult = max(0.3, risk / 1.5)

        for month in enrolled_months:
            num_claims = rng.poisson(config.avg_facility_claims_pmpm * volume_mult)

            for _ in range(num_claims):
                if not _should_generate_claim(rng, month, data_as_of, config.performance_year):
                    continue

                claim_counter += 1
                claim_id = f"CLM-F-{claim_counter:08d}"
                service_date = _random_date_in_month(rng, config.performance_year, month)
                svc_ts = pd.Timestamp(service_date)

                # Claim type: 5% inpatient, 15% ED, 80% outpatient facility
                type_roll = rng.random()
                if type_roll < 0.05:
                    # Inpatient
                    los = int(rng.integers(1, 10))
                    admission_date = service_date
                    discharge_date = (svc_ts + pd.Timedelta(days=los)).strftime("%Y-%m-%d")
                    drg_code, drg_desc = drg_codes[int(rng.integers(0, len(drg_codes)))]
                    pos = POS_CODES["inpatient"]
                    allowed = round(float(rng.uniform(5000, 50000)), 2)
                elif type_roll < 0.20:
                    # ED visit
                    admission_date = service_date
                    discharge_date = service_date
                    drg_code = None
                    drg_desc = None
                    pos = POS_CODES["ed"]
                    allowed = round(float(rng.uniform(500, 5000)), 2)
                else:
                    # Outpatient facility
                    admission_date = service_date
                    discharge_date = service_date
                    drg_code = None
                    drg_desc = None
                    pos = POS_CODES["outpatient"]
                    allowed = round(float(rng.uniform(100, 2000)), 2)

                paid = round(allowed * rng.uniform(0.80, 1.0), 2)
                patient_resp = round(allowed - paid, 2)

                rows.append({
                    "claim_id": claim_id,
                    "member_id": member_id,
                    "service_date": service_date,
                    "facility_npi": rng.choice(facility_npis),
                    "admission_date": admission_date,
                    "discharge_date": discharge_date,
                    "place_of_service": pos,
                    "drg_code": drg_code,
                    "revenue_code": rng.choice(revenue_codes),
                    "allowed_amount": allowed,
                    "paid_amount": paid,
                    "patient_responsibility": patient_resp,
                    "claim_status": "paid",
                    "adjudication_date": (svc_ts + pd.Timedelta(days=int(rng.integers(20, 75)))).strftime("%Y-%m-%d"),
                    "data_source": "payer_claims_feed",
                })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pharmacy claims
# ---------------------------------------------------------------------------

DRUG_CLASSES = [
    ("statin", "Atorvastatin", "49999-0001-01"),
    ("statin", "Rosuvastatin", "49999-0001-02"),
    ("diabetes", "Metformin", "49999-0002-01"),
    ("diabetes", "Insulin Glargine", "49999-0002-02"),
    ("diabetes", "Sitagliptin", "49999-0002-03"),
    ("antihypertensive", "Lisinopril", "49999-0003-01"),
    ("antihypertensive", "Amlodipine", "49999-0003-02"),
    ("antihypertensive", "Losartan", "49999-0003-03"),
    ("antidepressant", "Sertraline", "49999-0004-01"),
    ("antidepressant", "Escitalopram", "49999-0004-02"),
    ("ppi", "Omeprazole", "49999-0005-01"),
    ("analgesic", "Acetaminophen", "49999-0006-01"),
    ("anticoagulant", "Apixaban", "49999-0007-01"),
    ("bronchodilator", "Albuterol", "49999-0008-01"),
]


def generate_pharmacy_claims(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate pharmacy claims (~3.0 per member per month)."""
    rng = np.random.default_rng(config.seed + 4)

    perf_start = pd.Timestamp(config.performance_period_start)
    perf_end = pd.Timestamp(config.performance_period_end)
    data_as_of = pd.Timestamp(config.data_as_of_date)

    rows: list[dict] = []
    claim_counter = 0

    elig_lookup: dict[str, list[int]] = {}
    for mid in members_df["member_id"]:
        elig_lookup[mid] = _enrollment_months(mid, eligibility_df, perf_start, perf_end)

    for _, member in members_df.iterrows():
        member_id = member["member_id"]
        enrolled_months = elig_lookup.get(member_id, [])
        if not enrolled_months:
            continue

        risk = member["hcc_risk_score"]
        volume_mult = max(0.5, risk / 1.3)

        # Each member gets 2-5 chronic medications (depending on risk)
        num_chronic_meds = int(rng.integers(1, min(6, int(risk * 3) + 1)))
        member_meds = [
            DRUG_CLASSES[int(rng.integers(0, len(DRUG_CLASSES)))]
            for _ in range(num_chronic_meds)
        ]

        for month in enrolled_months:
            if not _should_generate_claim(rng, month, data_as_of, config.performance_year):
                continue

            # Fill each chronic med (with some gaps for adherence variation)
            for drug_class, drug_name, ndc in member_meds:
                # 80% chance of filling each month (creates adherence gaps)
                if rng.random() > 0.80:
                    continue

                claim_counter += 1
                fill_date = _random_date_in_month(rng, config.performance_year, month)
                days_supply = int(rng.choice([30, 60, 90], p=[0.70, 0.20, 0.10]))
                quantity = int(days_supply * rng.uniform(0.5, 2.0))
                allowed = round(float(rng.uniform(5, 300)), 2)
                paid = round(allowed * rng.uniform(0.70, 0.95), 2)

                rows.append({
                    "claim_id": f"CLM-RX-{claim_counter:08d}",
                    "member_id": member_id,
                    "fill_date": fill_date,
                    "ndc_code": ndc,
                    "drug_name": drug_name,
                    "drug_class": drug_class,
                    "days_supply": days_supply,
                    "quantity": quantity,
                    "allowed_amount": allowed,
                    "paid_amount": paid,
                    "data_source": "payer_claims_feed",
                })

            # Additional acute/one-off fills
            num_acute = rng.poisson(0.3 * volume_mult)
            for _ in range(num_acute):
                claim_counter += 1
                drug_class, drug_name, ndc = DRUG_CLASSES[int(rng.integers(0, len(DRUG_CLASSES)))]
                fill_date = _random_date_in_month(rng, config.performance_year, month)
                days_supply = int(rng.choice([7, 10, 14, 30]))
                quantity = int(days_supply)
                allowed = round(float(rng.uniform(5, 150)), 2)
                paid = round(allowed * rng.uniform(0.70, 0.95), 2)

                rows.append({
                    "claim_id": f"CLM-RX-{claim_counter:08d}",
                    "member_id": member_id,
                    "fill_date": fill_date,
                    "ndc_code": ndc,
                    "drug_name": drug_name,
                    "drug_class": drug_class,
                    "days_supply": days_supply,
                    "quantity": quantity,
                    "allowed_amount": allowed,
                    "paid_amount": paid,
                    "data_source": "payer_claims_feed",
                })

    return pd.DataFrame(rows)
