"""Generate a fake payer settlement report.

This report represents "what the payer calculated" — it intentionally diverges
from what the platform will calculate.  The discrepancy manifest documents exactly
where and why the numbers differ.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from generator.config import GenerationConfig


def generate_settlement_report(
    config: GenerationConfig,
    members_df: pd.DataFrame,
    providers_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
    claims_prof_df: pd.DataFrame,
    claims_facility_df: pd.DataFrame,
    claims_pharmacy_df: pd.DataFrame,
    clinical_screenings_df: pd.DataFrame,
    clinical_labs_df: pd.DataFrame,
    clinical_vitals_df: pd.DataFrame,
    discrepancy_manifest: dict,
) -> dict:
    """Build the payer settlement report JSON.

    The report is constructed to be *close* to what the platform will compute
    but with deliberate differences aligned to the planted discrepancies.
    """
    rng = np.random.default_rng(config.seed + 200)

    # -----------------------------------------------------------------------
    # Attribution numbers
    # -----------------------------------------------------------------------
    # Start from realistic baseline, then adjust for discrepancies
    # The platform will attribute ~850-870 members; the payer's number differs
    # because of the 23 attribution discrepancies.
    platform_only_count = sum(
        1 for d in discrepancy_manifest["attribution_discrepancies"]
        if d["type"] == "platform_only"
    )
    payer_only_count = sum(
        1 for d in discrepancy_manifest["attribution_discrepancies"]
        if d["type"] == "payer_only"
    )

    # Base attributed count that the platform will compute (~865)
    base_attributed = 865
    # Payer's count: subtract platform-only, add payer-only
    payer_attributed = base_attributed - platform_only_count + payer_only_count
    payer_step1 = int(payer_attributed * 0.85)
    payer_step2 = payer_attributed - payer_step1

    # -----------------------------------------------------------------------
    # Quality scores — slightly different from platform due to discrepancies
    # -----------------------------------------------------------------------
    # These are the payer's numbers.  The platform will compute different
    # numerators/denominators because of EHR-only data and exclusion differences.

    hba1c_denominator = int(rng.integers(165, 180))
    hba1c_numerator = int(hba1c_denominator * rng.uniform(0.20, 0.25))
    hba1c_rate = round(hba1c_numerator / hba1c_denominator * 100, 1)

    bp_denominator = int(rng.integers(380, 410))
    bp_numerator = int(bp_denominator * rng.uniform(0.62, 0.68))
    bp_rate = round(bp_numerator / bp_denominator * 100, 1)

    bcs_denominator = int(rng.integers(175, 195))
    bcs_numerator = int(bcs_denominator * rng.uniform(0.68, 0.74))
    bcs_rate = round(bcs_numerator / bcs_denominator * 100, 1)

    crc_denominator = int(rng.integers(300, 330))
    crc_numerator = int(crc_denominator * rng.uniform(0.60, 0.66))
    crc_rate = round(crc_numerator / crc_denominator * 100, 1)

    dep_denominator = int(rng.integers(790, 825))
    dep_numerator = int(dep_denominator * rng.uniform(0.50, 0.55))
    dep_rate = round(dep_numerator / dep_denominator * 100, 1)

    # Composite: average of measure rates (for non-inverse measures, use rate;
    # for inverse HbA1c, use 100 - rate)
    composite = round(
        ((100 - hba1c_rate) + bp_rate + bcs_rate + crc_rate + dep_rate) / 5, 1
    )

    # -----------------------------------------------------------------------
    # Cost numbers
    # -----------------------------------------------------------------------
    benchmark_pmpm = 1187.00
    # Payer's PMPM is slightly different because of cost discrepancies
    actual_pmpm = round(float(rng.uniform(1130, 1155)), 2)

    member_months = payer_attributed * int(rng.integers(10, 12))
    total_benchmark = round(benchmark_pmpm * member_months, 0)
    total_actual = round(actual_pmpm * member_months, 0)
    gross_savings = round(total_benchmark - total_actual, 0)

    savings_rate = round((benchmark_pmpm - actual_pmpm) / benchmark_pmpm, 4)
    msr = 0.02
    shared_savings_rate = 0.50

    if savings_rate > msr and composite >= 40.0:
        shared_savings_amount = round(gross_savings * shared_savings_rate, 0)
    else:
        shared_savings_amount = 0

    # -----------------------------------------------------------------------
    # Assemble report
    # -----------------------------------------------------------------------
    report = {
        "report_metadata": {
            "payer": "CMS / Medicare Shared Savings Program",
            "contract_id": "CONTRACT-MSSP-2025",
            "performance_year": config.performance_year,
            "report_date": "2026-03-15",
            "report_type": "preliminary_settlement",
        },
        "attribution": {
            "total_attributed": payer_attributed,
            "attributed_by_step1": payer_step1,
            "attributed_by_step2": payer_step2,
        },
        "quality": {
            "composite_score": composite,
            "measures": {
                "hba1c_poor_control": {
                    "rate": hba1c_rate,
                    "numerator": hba1c_numerator,
                    "denominator": hba1c_denominator,
                },
                "controlling_bp": {
                    "rate": bp_rate,
                    "numerator": bp_numerator,
                    "denominator": bp_denominator,
                },
                "breast_cancer_screening": {
                    "rate": bcs_rate,
                    "numerator": bcs_numerator,
                    "denominator": bcs_denominator,
                },
                "colorectal_screening": {
                    "rate": crc_rate,
                    "numerator": crc_numerator,
                    "denominator": crc_denominator,
                },
                "depression_screening": {
                    "rate": dep_rate,
                    "numerator": dep_numerator,
                    "denominator": dep_denominator,
                },
            },
        },
        "cost": {
            "benchmark_pmpm": benchmark_pmpm,
            "actual_pmpm": actual_pmpm,
            "total_benchmark": total_benchmark,
            "total_actual": total_actual,
            "gross_savings": gross_savings,
            "minimum_savings_rate": msr,
            "savings_rate_achieved": savings_rate,
            "shared_savings_rate": shared_savings_rate,
            "shared_savings_amount": shared_savings_amount,
        },
    }

    return report
