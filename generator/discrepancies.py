"""Plant intentional discrepancies in the generated data.

These discrepancies are the stars of the reconciliation demo.  They are
specific, traceable, and realistic.  A manifest file is written so the
reconciliation engine's output can be validated — but the engine itself
must NEVER read the manifest.

Discrepancy counts (from config):
  - 23 attribution (12 platform-only, 7 payer-only, 4 different-provider)
  - 15 quality measure (8 EHR-only, 4 payer-exclusion, 3 screening-conflict)
  - 8 cost (5 run-out timing, 3 amount differences)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from generator.config import GenerationConfig


def plant_discrepancies(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
    claims_prof_df: pd.DataFrame,
    claims_facility_df: pd.DataFrame,
    claims_pharmacy_df: pd.DataFrame,
    clinical_labs_df: pd.DataFrame,
    clinical_screenings_df: pd.DataFrame,
    clinical_vitals_df: pd.DataFrame,
) -> dict:
    """Plant discrepancies and return the manifest documenting them.

    The DataFrames are modified **in place** where needed (e.g., adding
    extra EHR-only records, modifying claim amounts).

    Returns
    -------
    dict
        The discrepancy manifest — written to disk by the caller.
    """
    rng = np.random.default_rng(config.seed + 100)

    manifest: dict = {
        "description": "Planted discrepancies for reconciliation demo validation",
        "seed": config.seed,
        "attribution_discrepancies": [],
        "quality_discrepancies": [],
        "cost_discrepancies": [],
    }

    # Pools of member IDs to draw from (exclude deceased / very short enrollment)
    eligible_ids = members_df[
        members_df["deceased_date"].isna() | (members_df["deceased_date"] == "")
    ]["member_id"].tolist()

    # Shuffle so we pick different members for each category
    rng.shuffle(eligible_ids)
    cursor = 0

    pcp_npis = providers_df[providers_df["is_pcp"] == True]["npi"].tolist()

    # Terminated provider NPIs
    terminated = providers_df[providers_df["termination_date"].notna()]
    terminated_npis = terminated["npi"].tolist()

    # -----------------------------------------------------------------------
    # 1. ATTRIBUTION DISCREPANCIES (23 total)
    # -----------------------------------------------------------------------

    # --- 12 platform-only attributions ---
    # Reason: payer's earlier run-out window missed late-arriving claims that
    # establish plurality.  We add E&M claims for these members from a PCP
    # with service dates in recent months (which fall outside the payer's
    # cutoff but inside the platform's window).
    platform_only_ids = eligible_ids[cursor:cursor + 12]
    cursor += 12

    for mid in platform_only_ids:
        # Add 2-3 late-arriving E&M claims (service month Sep/Oct 2025)
        pcp = members_df.loc[members_df["member_id"] == mid, "pcp_npi"].iloc[0]
        for _ in range(int(rng.integers(2, 4))):
            month = int(rng.choice([9, 10]))
            day = int(rng.integers(1, 29))
            new_claim = {
                "claim_id": f"CLM-P-D{rng.integers(10000000, 99999999):08d}",
                "member_id": mid,
                "service_date": f"2025-{month:02d}-{day:02d}",
                "rendering_npi": pcp,
                "billing_npi": pcp,
                "place_of_service": "11",
                "procedure_code": rng.choice(["99213", "99214"]),
                "procedure_description": "Office visit, established patient",
                "modifier": None,
                "diagnosis_code_1": "Z00.00",
                "diagnosis_description_1": "General exam",
                "diagnosis_code_2": None,
                "diagnosis_code_3": None,
                "diagnosis_code_4": None,
                "allowed_amount": round(float(rng.uniform(100, 200)), 2),
                "paid_amount": round(float(rng.uniform(80, 180)), 2),
                "patient_responsibility": round(float(rng.uniform(5, 30)), 2),
                "claim_status": "paid",
                "adjudication_date": f"2025-{min(month + 2, 12):02d}-15",
                "data_source": "payer_claims_feed",
            }
            claims_prof_df.loc[len(claims_prof_df)] = new_claim

        manifest["attribution_discrepancies"].append({
            "member_id": mid,
            "type": "platform_only",
            "reason": "Late-arriving claims establish plurality for platform but fall outside payer run-out window",
            "financial_impact_estimate": round(float(rng.uniform(800, 2500)), 2),
        })

    # --- 7 payer-only attributions ---
    # Reason: payer included claims from a provider whose ACO participation
    # terminated mid-year.  The platform correctly excludes post-termination claims.
    payer_only_ids = eligible_ids[cursor:cursor + 7]
    cursor += 7

    for mid in payer_only_ids:
        # Replace this member's majority PCP visits with a terminated provider
        if terminated_npis:
            term_npi = rng.choice(terminated_npis)
        else:
            term_npi = pcp_npis[-1]  # fallback

        # Add visits to the terminated provider (post-termination dates)
        for _ in range(3):
            month = int(rng.choice([7, 8, 9]))
            day = int(rng.integers(1, 29))
            new_claim = {
                "claim_id": f"CLM-P-D{rng.integers(10000000, 99999999):08d}",
                "member_id": mid,
                "service_date": f"2025-{month:02d}-{day:02d}",
                "rendering_npi": term_npi,
                "billing_npi": term_npi,
                "place_of_service": "11",
                "procedure_code": rng.choice(["99213", "99214", "99215"]),
                "procedure_description": "Office visit, established patient",
                "modifier": None,
                "diagnosis_code_1": "I10",
                "diagnosis_description_1": "Essential hypertension",
                "diagnosis_code_2": None,
                "diagnosis_code_3": None,
                "diagnosis_code_4": None,
                "allowed_amount": round(float(rng.uniform(100, 200)), 2),
                "paid_amount": round(float(rng.uniform(80, 180)), 2),
                "patient_responsibility": round(float(rng.uniform(5, 30)), 2),
                "claim_status": "paid",
                "adjudication_date": f"2025-{min(month + 1, 12):02d}-20",
                "data_source": "payer_claims_feed",
            }
            claims_prof_df.loc[len(claims_prof_df)] = new_claim

        manifest["attribution_discrepancies"].append({
            "member_id": mid,
            "type": "payer_only",
            "reason": "Payer includes post-termination claims from provider; platform excludes them per contract",
            "terminated_npi": term_npi,
            "financial_impact_estimate": round(float(rng.uniform(600, 2000)), 2),
        })

    # --- 4 different-provider attributions ---
    # Reason: tie in plurality, broken differently (payer uses alphabetical NPI,
    # platform uses most recent visit date).
    diff_provider_ids = eligible_ids[cursor:cursor + 4]
    cursor += 4

    for mid in diff_provider_ids:
        # Give this member exactly equal visits to two different PCPs
        pcp_a = pcp_npis[int(rng.integers(0, len(pcp_npis)))]
        pcp_b_candidates = [p for p in pcp_npis if p != pcp_a]
        pcp_b = rng.choice(pcp_b_candidates)

        # 3 visits to each, but PCP B has the most recent visit
        for i, pcp in enumerate([pcp_a, pcp_b]):
            for visit_num in range(3):
                if pcp == pcp_b and visit_num == 2:
                    # Most recent visit
                    svc_date = "2025-09-15"
                elif pcp == pcp_a and visit_num == 2:
                    svc_date = "2025-08-10"
                else:
                    month = int(rng.integers(1, 8))
                    day = int(rng.integers(1, 29))
                    svc_date = f"2025-{month:02d}-{day:02d}"

                new_claim = {
                    "claim_id": f"CLM-P-D{rng.integers(10000000, 99999999):08d}",
                    "member_id": mid,
                    "service_date": svc_date,
                    "rendering_npi": pcp,
                    "billing_npi": pcp,
                    "place_of_service": "11",
                    "procedure_code": "99213",
                    "procedure_description": "Office visit, established patient",
                    "modifier": None,
                    "diagnosis_code_1": "Z00.00",
                    "diagnosis_description_1": "General exam",
                    "diagnosis_code_2": None,
                    "diagnosis_code_3": None,
                    "diagnosis_code_4": None,
                    "allowed_amount": 150.00,
                    "paid_amount": 130.00,
                    "patient_responsibility": 20.00,
                    "claim_status": "paid",
                    "adjudication_date": "2025-10-01",
                    "data_source": "payer_claims_feed",
                }
                claims_prof_df.loc[len(claims_prof_df)] = new_claim

        # Platform picks PCP B (most recent visit), payer picks min(NPI) alphabetically
        platform_npi = pcp_b
        payer_npi = min(pcp_a, pcp_b)  # alphabetical

        manifest["attribution_discrepancies"].append({
            "member_id": mid,
            "type": "different_provider",
            "reason": "Plurality tie broken differently — platform uses most recent visit, payer uses alphabetical NPI",
            "platform_attributed_npi": platform_npi,
            "payer_attributed_npi": payer_npi,
            "financial_impact_estimate": round(float(rng.uniform(200, 800)), 2),
        })

    # -----------------------------------------------------------------------
    # 2. QUALITY MEASURE DISCREPANCIES (15 total)
    # -----------------------------------------------------------------------

    # --- 8 EHR-only data ---
    # Platform has EHR lab results (e.g., HbA1c values) that the payer doesn't
    # see.  The payer only sees the lab order CPT code, not the result.
    ehr_only_ids = eligible_ids[cursor:cursor + 8]
    cursor += 8

    for mid in ehr_only_ids:
        ordering_npi = members_df.loc[
            members_df["member_id"] == mid, "pcp_npi"
        ].iloc[0]

        # Add an EHR HbA1c result showing control — no matching CPT in claims
        lab_date = f"2025-{int(rng.integers(3, 9)):02d}-{int(rng.integers(1, 29)):02d}"
        a1c_value = round(float(rng.uniform(6.0, 7.8)), 1)

        clinical_labs_df.loc[len(clinical_labs_df)] = {
            "member_id": mid,
            "lab_date": lab_date,
            "loinc_code": "4548-4",
            "lab_name": "Hemoglobin A1c",
            "result_value": a1c_value,
            "result_unit": "%",
            "reference_range": "4.0-5.6",
            "abnormal_flag": "H" if a1c_value > 5.6 else None,
            "ordering_npi": ordering_npi,
            "data_source": "ehr",
        }

        manifest["quality_discrepancies"].append({
            "member_id": mid,
            "type": "ehr_only_data",
            "measure": "hba1c_poor_control",
            "reason": "Platform uses EHR lab result showing HbA1c control; payer lacks the result value",
            "ehr_value": a1c_value,
        })

    # --- 4 payer exclusions ---
    # Payer excludes members from a measure denominator based on a claims
    # record (e.g., hospice) that doesn't appear in the platform's feed.
    payer_excl_ids = eligible_ids[cursor:cursor + 4]
    cursor += 4

    for mid in payer_excl_ids:
        manifest["quality_discrepancies"].append({
            "member_id": mid,
            "type": "payer_exclusion",
            "measure": rng.choice([
                "controlling_bp", "breast_cancer_screening", "colorectal_screening",
            ]),
            "reason": "Payer applies hospice exclusion based on claim not in platform data feed",
        })

    # --- 3 screening conflicts ---
    # EHR shows a screening completed; no corresponding CPT in claims.
    screening_conflict_ids = eligible_ids[cursor:cursor + 3]
    cursor += 3

    for mid in screening_conflict_ids:
        ordering_npi = members_df.loc[
            members_df["member_id"] == mid, "pcp_npi"
        ].iloc[0]

        scr_type = rng.choice(["colonoscopy", "mammogram", "depression_screening"])
        cpt_map = {
            "colonoscopy": "45378",
            "mammogram": "77067",
            "depression_screening": "96127",
        }
        scr_date = f"2025-{int(rng.integers(2, 9)):02d}-{int(rng.integers(1, 29)):02d}"

        clinical_screenings_df.loc[len(clinical_screenings_df)] = {
            "member_id": mid,
            "screening_date": scr_date,
            "screening_type": scr_type,
            "cpt_code": cpt_map[scr_type],
            "result": "normal",
            "ordering_npi": ordering_npi,
            "data_source": "ehr",
        }

        manifest["quality_discrepancies"].append({
            "member_id": mid,
            "type": "screening_conflict",
            "measure": scr_type,
            "reason": "EHR has screening record but no corresponding claim exists — screening may have been billed under a different code or denied",
            "screening_date": scr_date,
        })

    # -----------------------------------------------------------------------
    # 3. COST DISCREPANCIES (8 total, aggregate to ~$47K impact)
    # -----------------------------------------------------------------------

    # --- 5 run-out timing ---
    # High-cost claims present in platform data but not in payer settlement calc.
    runout_ids = eligible_ids[cursor:cursor + 5]
    cursor += 5

    target_total_impact = 47000.0
    amount_per_runout = target_total_impact * 0.75 / 5  # ~$7,050 each

    for mid in runout_ids:
        amount = round(float(rng.uniform(amount_per_runout * 0.7, amount_per_runout * 1.3)), 2)

        # Add a high-cost claim with late adjudication date
        month = int(rng.choice([7, 8, 9]))
        day = int(rng.integers(1, 29))
        svc_date = f"2025-{month:02d}-{day:02d}"
        adj_date = f"2026-01-{int(rng.integers(5, 28)):02d}"  # adjudicated in Jan 2026

        new_claim = {
            "claim_id": f"CLM-P-D{rng.integers(10000000, 99999999):08d}",
            "member_id": mid,
            "service_date": svc_date,
            "rendering_npi": rng.choice(pcp_npis),
            "billing_npi": rng.choice(pcp_npis),
            "place_of_service": "11",
            "procedure_code": "99215",
            "procedure_description": "Office visit, high complexity",
            "modifier": None,
            "diagnosis_code_1": "E11.9",
            "diagnosis_description_1": "Type 2 diabetes",
            "diagnosis_code_2": None,
            "diagnosis_code_3": None,
            "diagnosis_code_4": None,
            "allowed_amount": amount,
            "paid_amount": round(amount * 0.85, 2),
            "patient_responsibility": round(amount * 0.15, 2),
            "claim_status": "paid",
            "adjudication_date": adj_date,
            "data_source": "payer_claims_feed",
        }
        claims_prof_df.loc[len(claims_prof_df)] = new_claim

        manifest["cost_discrepancies"].append({
            "member_id": mid,
            "type": "runout_timing",
            "reason": "Claim adjudicated after payer settlement cutoff but within platform window",
            "claim_amount": amount,
            "service_date": svc_date,
            "adjudication_date": adj_date,
        })

    # --- 3 amount differences ---
    # Claims with different allowed amounts between platform feed and payer settlement.
    amount_diff_ids = eligible_ids[cursor:cursor + 3]
    cursor += 3
    remaining_impact = target_total_impact * 0.25 / 3  # ~$3,917 each

    for mid in amount_diff_ids:
        diff = round(float(rng.uniform(remaining_impact * 0.6, remaining_impact * 1.4)), 2)

        manifest["cost_discrepancies"].append({
            "member_id": mid,
            "type": "amount_difference",
            "reason": "Claim reprocessed/adjusted after platform received data extract — allowed amount differs",
            "amount_difference": diff,
        })

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    manifest["summary"] = {
        "total_attribution_discrepancies": len(manifest["attribution_discrepancies"]),
        "attribution_platform_only": sum(
            1 for d in manifest["attribution_discrepancies"] if d["type"] == "platform_only"
        ),
        "attribution_payer_only": sum(
            1 for d in manifest["attribution_discrepancies"] if d["type"] == "payer_only"
        ),
        "attribution_different_provider": sum(
            1 for d in manifest["attribution_discrepancies"] if d["type"] == "different_provider"
        ),
        "total_quality_discrepancies": len(manifest["quality_discrepancies"]),
        "total_cost_discrepancies": len(manifest["cost_discrepancies"]),
        "estimated_total_financial_impact": round(
            sum(d.get("financial_impact_estimate", 0) for d in manifest["attribution_discrepancies"])
            + sum(d.get("claim_amount", 0) for d in manifest["cost_discrepancies"])
            + sum(d.get("amount_difference", 0) for d in manifest["cost_discrepancies"]),
            2,
        ),
    }

    return manifest
