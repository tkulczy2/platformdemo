"""Orchestrate synthetic data generation.

Run:  python -m generator.generate

Generates all synthetic data files to data/synthetic/.
Parameterized via GenerationConfig — modify config.py to change population
size, data quality issues, or discrepancy counts.

The generator is deterministic: same seed produces identical data.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd

from generator.config import GenerationConfig
from generator.providers import generate_providers
from generator.members import generate_members
from generator.eligibility import generate_eligibility
from generator.claims import (
    generate_professional_claims,
    generate_facility_claims,
    generate_pharmacy_claims,
)
from generator.clinical import (
    generate_clinical_labs,
    generate_clinical_screenings,
    generate_clinical_vitals,
)
from generator.discrepancies import plant_discrepancies
from generator.settlement import generate_settlement_report


def generate(config: GenerationConfig | None = None) -> None:
    """Run the full generation pipeline."""
    if config is None:
        config = GenerationConfig()

    output_dir = Path("data/synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)

    contracts_dir = Path("data/contracts")
    contracts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating synthetic data with seed={config.seed} ...")
    t0 = time.time()

    # ------------------------------------------------------------------
    # Step 1: Providers (no dependencies)
    # ------------------------------------------------------------------
    print("  [1/9] Generating providers ...")
    providers_df = generate_providers(config)
    providers_df.to_csv(output_dir / "providers.csv", index=False)
    print(f"         → {len(providers_df)} providers")

    # ------------------------------------------------------------------
    # Step 2: Members (depends on providers for PCP assignment)
    # ------------------------------------------------------------------
    print("  [2/9] Generating members ...")
    members_df = generate_members(config, providers_df)
    members_df.to_csv(output_dir / "members.csv", index=False)
    print(f"         → {len(members_df)} members")

    # ------------------------------------------------------------------
    # Step 3: Eligibility (depends on members)
    # ------------------------------------------------------------------
    print("  [3/9] Generating eligibility ...")
    eligibility_df = generate_eligibility(config, members_df)
    eligibility_df.to_csv(output_dir / "eligibility.csv", index=False)
    print(f"         → {len(eligibility_df)} eligibility records")

    # ------------------------------------------------------------------
    # Step 4: Professional claims (depends on members, providers, eligibility)
    # ------------------------------------------------------------------
    print("  [4/9] Generating professional claims ...")
    claims_prof_df = generate_professional_claims(
        config, members_df, providers_df, eligibility_df
    )
    print(f"         → {len(claims_prof_df)} professional claims (pre-discrepancy)")

    # ------------------------------------------------------------------
    # Step 5: Facility claims
    # ------------------------------------------------------------------
    print("  [5/9] Generating facility claims ...")
    claims_facility_df = generate_facility_claims(
        config, members_df, providers_df, eligibility_df
    )
    print(f"         → {len(claims_facility_df)} facility claims")

    # ------------------------------------------------------------------
    # Step 6: Pharmacy claims
    # ------------------------------------------------------------------
    print("  [6/9] Generating pharmacy claims ...")
    claims_pharmacy_df = generate_pharmacy_claims(
        config, members_df, eligibility_df
    )
    print(f"         → {len(claims_pharmacy_df)} pharmacy claims")

    # ------------------------------------------------------------------
    # Step 7: Clinical data (labs, screenings, vitals)
    # ------------------------------------------------------------------
    print("  [7/9] Generating clinical data ...")
    clinical_labs_df = generate_clinical_labs(config, members_df, providers_df)
    clinical_screenings_df = generate_clinical_screenings(config, members_df, providers_df)
    clinical_vitals_df = generate_clinical_vitals(config, members_df, providers_df)
    print(f"         → {len(clinical_labs_df)} lab results")
    print(f"         → {len(clinical_screenings_df)} screening records")
    print(f"         → {len(clinical_vitals_df)} vital signs")

    # ------------------------------------------------------------------
    # Step 8: Plant discrepancies (modifies DataFrames in place)
    # ------------------------------------------------------------------
    print("  [8/9] Planting discrepancies ...")
    discrepancy_manifest = plant_discrepancies(
        config,
        members_df,
        providers_df,
        eligibility_df,
        claims_prof_df,
        claims_facility_df,
        claims_pharmacy_df,
        clinical_labs_df,
        clinical_screenings_df,
        clinical_vitals_df,
    )
    print(f"         → {discrepancy_manifest['summary']['total_attribution_discrepancies']} attribution discrepancies")
    print(f"         → {discrepancy_manifest['summary']['total_quality_discrepancies']} quality discrepancies")
    print(f"         → {discrepancy_manifest['summary']['total_cost_discrepancies']} cost discrepancies")

    # Save CSVs (after discrepancy modifications)
    claims_prof_df.to_csv(output_dir / "claims_professional.csv", index=False)
    claims_facility_df.to_csv(output_dir / "claims_facility.csv", index=False)
    claims_pharmacy_df.to_csv(output_dir / "claims_pharmacy.csv", index=False)
    clinical_labs_df.to_csv(output_dir / "clinical_labs.csv", index=False)
    clinical_screenings_df.to_csv(output_dir / "clinical_screenings.csv", index=False)
    clinical_vitals_df.to_csv(output_dir / "clinical_vitals.csv", index=False)

    # Save discrepancy manifest
    with open(output_dir / "discrepancy_manifest.json", "w") as f:
        json.dump(discrepancy_manifest, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Step 9: Payer settlement report
    # ------------------------------------------------------------------
    print("  [9/9] Generating payer settlement report ...")
    settlement_report = generate_settlement_report(
        config,
        members_df,
        providers_df,
        eligibility_df,
        claims_prof_df,
        claims_facility_df,
        claims_pharmacy_df,
        clinical_screenings_df,
        clinical_labs_df,
        clinical_vitals_df,
        discrepancy_manifest,
    )
    with open(output_dir / "payer_settlement_report.json", "w") as f:
        json.dump(settlement_report, f, indent=2)

    # ------------------------------------------------------------------
    # Generate sample MSSP contract
    # ------------------------------------------------------------------
    _generate_sample_contract(contracts_dir)

    elapsed = time.time() - t0
    print(f"\nDone! Generated all data in {elapsed:.1f}s")
    print(f"Output directory: {output_dir.resolve()}")

    # Quick validation
    _validate(output_dir)


def _generate_sample_contract(contracts_dir: Path) -> None:
    """Write the sample MSSP contract JSON."""
    contract = {
        "contract_id": "CONTRACT-MSSP-2025",
        "contract_name": "Medicare Shared Savings Program — ACO Agreement 2025",
        "performance_year": 2025,
        "clauses": {
            "eligibility": {
                "clause_id": "ELIG-1.0",
                "text": "Beneficiaries must have at least one month of enrollment during the performance year and must not be enrolled in a Medicare Advantage plan, have end-stage renal disease, or reside outside the ACO's service area to be eligible for attribution.",
                "parameters": {
                    "minimum_enrollment_months": 1,
                    "exclude_esrd": True,
                    "exclude_medicare_advantage": True,
                    "service_area_required": True,
                },
            },
            "attribution_step1": {
                "clause_id": "ATTR-1.1",
                "text": "Step 1: Assign each eligible beneficiary to the ACO participant (TIN/NPI) that provided the plurality of primary care services, as defined by CPT codes 99201-99215, 99381-99397, and G0438-G0439, during the most recent 12-month period.",
                "parameters": {
                    "attribution_method": "plurality",
                    "qualifying_cpt_codes": [
                        "99201", "99202", "99203", "99204", "99205",
                        "99211", "99212", "99213", "99214", "99215",
                        "99381", "99382", "99383", "99384", "99385",
                        "99386", "99387", "99391", "99392", "99393",
                        "99394", "99395", "99396", "99397",
                        "G0438", "G0439",
                    ],
                    "provider_filter_step1": "pcp_only",
                    "lookback_months": 12,
                },
            },
            "attribution_step2": {
                "clause_id": "ATTR-1.2",
                "text": "Step 2: For beneficiaries not assigned in Step 1, assign based on the plurality of primary care services provided by any ACO participant, including specialists who rendered qualifying primary care codes.",
                "parameters": {
                    "provider_filter_step2": "all_aco_participants",
                },
            },
            "attribution_tiebreaker": {
                "clause_id": "ATTR-1.3",
                "text": "In the event of a tie in service counts, the beneficiary shall be assigned to the provider whose most recent qualifying service was most recent in time.",
                "parameters": {
                    "tiebreaker": "most_recent_visit",
                },
            },
            "quality_measures": {
                "clause_id": "QUAL-1.0",
                "text": "The ACO's quality performance shall be evaluated across the following measures, each weighted equally at 20% of the composite score.",
                "parameters": {
                    "measures": [
                        "hba1c_poor_control",
                        "controlling_bp",
                        "breast_cancer_screening",
                        "colorectal_screening",
                        "depression_screening",
                    ],
                    "measure_weights": {
                        "hba1c_poor_control": 0.20,
                        "controlling_bp": 0.20,
                        "breast_cancer_screening": 0.20,
                        "colorectal_screening": 0.20,
                        "depression_screening": 0.20,
                    },
                    "conflict_resolution": "most_recent_clinical",
                },
            },
            "cost_calculation": {
                "clause_id": "COST-1.0",
                "text": "Total cost of care shall be calculated as the sum of all Parts A and B allowed charges for attributed beneficiaries during the performance year, divided by the number of attributed beneficiary-months, expressed as a per-member-per-month (PMPM) amount. Claims with service dates within the performance year that are adjudicated within 3 months of the performance year end shall be included.",
                "parameters": {
                    "cost_basis": "allowed_amount",
                    "include_pharmacy": False,
                    "runout_months": 3,
                },
            },
            "settlement": {
                "clause_id": "SETTLE-1.0",
                "text": "The ACO's benchmark shall be $1,187.00 PMPM, as established by CMS based on the ACO's historical cost baseline trended forward. If the ACO's actual PMPM is below the benchmark by more than the minimum savings rate of 2.0%, the ACO shall receive 50% of the gross savings, subject to quality performance gates.",
                "parameters": {
                    "benchmark_pmpm": 1187.00,
                    "minimum_savings_rate": 0.02,
                    "shared_savings_rate": 0.50,
                },
            },
            "quality_gate": {
                "clause_id": "SETTLE-1.1",
                "text": "The quality performance gate requires a minimum composite quality score of 40% for the ACO to be eligible for any shared savings.",
                "parameters": {
                    "quality_gate_threshold": 0.40,
                },
            },
        },
    }

    with open(contracts_dir / "sample_mssp_contract.json", "w") as f:
        json.dump(contract, f, indent=2)


def _validate(output_dir: Path) -> None:
    """Run basic validation on generated data."""
    print("\nValidation:")

    # Check expected files
    expected_csvs = [
        "members.csv", "providers.csv", "eligibility.csv",
        "claims_professional.csv", "claims_facility.csv", "claims_pharmacy.csv",
        "clinical_labs.csv", "clinical_screenings.csv", "clinical_vitals.csv",
    ]
    expected_jsons = ["discrepancy_manifest.json", "payer_settlement_report.json"]

    for fname in expected_csvs:
        path = output_dir / fname
        if path.exists():
            df = pd.read_csv(path)
            print(f"  ✓ {fname}: {len(df)} rows")
        else:
            print(f"  ✗ {fname}: MISSING")

    for fname in expected_jsons:
        path = output_dir / fname
        if path.exists():
            print(f"  ✓ {fname}: exists")
        else:
            print(f"  ✗ {fname}: MISSING")

    # Specific validations
    members = pd.read_csv(output_dir / "members.csv")
    claims = pd.read_csv(output_dir / "claims_professional.csv")
    providers = pd.read_csv(output_dir / "providers.csv")

    assert len(members) == 1000, f"Expected 1000 members, got {len(members)}"
    print(f"  ✓ Members count: {len(members)}")

    assert len(claims) > 40000, f"Expected >40000 professional claims, got {len(claims)}"
    print(f"  ✓ Professional claims count: {len(claims)}")

    # Check referential integrity
    claim_members = set(claims["member_id"].unique())
    member_ids = set(members["member_id"].unique())
    orphan_claims = claim_members - member_ids
    if orphan_claims:
        print(f"  ✗ {len(orphan_claims)} claims reference non-existent members")
    else:
        print(f"  ✓ All claim member_ids exist in members.csv")

    claim_npis = set(claims["rendering_npi"].dropna().unique())
    provider_npis = set(providers["npi"].unique())
    orphan_npis = claim_npis - provider_npis
    if orphan_npis:
        print(f"  ⚠ {len(orphan_npis)} claims reference NPIs not in providers.csv (may include discrepancy-planted claims)")
    else:
        print(f"  ✓ All claim NPIs exist in providers.csv")


if __name__ == "__main__":
    generate()
