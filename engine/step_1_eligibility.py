"""Step 1: Eligibility Determination — enrollment continuity and exclusion criteria.

Contract clause (ELIG-1.0):
    "Beneficiaries must have at least one month of enrollment during the
     performance year and must not be enrolled in a Medicare Advantage plan,
     have end-stage renal disease, or reside outside the ACO's service area
     to be eligible for attribution."
"""

import inspect
import time

import pandas as pd

from engine.data_loader import LoadedData
from engine.provenance import (
    CodeReference,
    ContractClause,
    DataReference,
    MemberDetail,
    StepResult,
)


def determine_eligibility(data: LoadedData, contract: dict) -> StepResult:
    """Determine which members are eligible for attribution based on contract rules."""
    start = time.time()

    elig_clause = contract["clauses"]["eligibility"]
    params = elig_clause["parameters"]
    min_months = params.get("minimum_enrollment_months", 1)
    exclude_esrd = params.get("exclude_esrd", True)
    service_area_required = params.get("service_area_required", True)

    contract_clause = ContractClause(
        clause_id=elig_clause["clause_id"],
        clause_text=elig_clause["text"],
        interpretation=(
            f"Members must have at least {min_months} month(s) of enrollment "
            f"during the performance year. "
            f"{'ESRD exclusion is applied. ' if exclude_esrd else ''}"
            f"{'Service area residency is required.' if service_area_required else ''}"
        ),
        parameters_extracted=params,
    )

    perf_year = contract.get("performance_year", 2025)
    perf_start = pd.Timestamp(f"{perf_year}-01-01")
    perf_end = pd.Timestamp(f"{perf_year}-12-31")

    members = data.members
    eligibility = data.eligibility
    claims_pro = data.claims_professional

    # Build service area zip set from config
    from generator.config import GenerationConfig
    config = GenerationConfig()
    service_area_zips = set(config.service_area_zips)

    # Pre-compute enrollment months per member (vectorized)
    enrollment_months_map = _calc_all_enrollment_months(eligibility, perf_start, perf_end)

    # Pre-compute ESRD members: N18.6 as primary dx on dialysis-related claims
    esrd_member_ids = set()
    esrd_claims_by_member = {}
    if exclude_esrd:
        dialysis_cpt_prefixes = ("9093", "9094", "9095", "9096", "9097", "9098", "9099", "99512")
        mask = claims_pro["diagnosis_code_1"] == "N18.6"
        esrd_candidates = claims_pro[mask]
        if not esrd_candidates.empty:
            proc_mask = esrd_candidates["procedure_code"].apply(
                lambda x: any(str(x).startswith(p) for p in dialysis_cpt_prefixes) if pd.notna(x) else False
            )
            esrd_claims_df = esrd_candidates[proc_mask]
            esrd_member_ids = set(esrd_claims_df["member_id"].unique())
            for mid, group in esrd_claims_df.groupby("member_id"):
                esrd_claims_by_member[mid] = group.index.tolist()

    # Pre-compute eligibility row indices per member
    elig_by_member = {}
    for mid, group in eligibility.groupby("member_id"):
        elig_by_member[mid] = group.index.tolist()

    member_details = []
    eligible_member_ids = []
    data_quality_flags = []

    for idx, member in members.iterrows():
        member_id = member["member_id"]
        reasons_excluded = []
        data_refs = []

        enrollment_months = enrollment_months_map.get(member_id, 0)
        elig_row_indices = elig_by_member.get(member_id, [])

        data_refs.append(DataReference(
            source_file="eligibility.csv",
            row_indices=elig_row_indices,
            columns_used=["member_id", "enrollment_start_date", "enrollment_end_date"],
            description=f"{len(elig_row_indices)} eligibility record(s), {enrollment_months} month(s) enrolled",
        ))

        # Check minimum enrollment
        if enrollment_months < min_months:
            reasons_excluded.append(
                f"Insufficient enrollment: {enrollment_months} month(s) < minimum {min_months}"
            )

        # Check ESRD exclusion
        if exclude_esrd and member_id in esrd_member_ids:
            reasons_excluded.append("ESRD diagnosis (ICD-10: N18.6) on dialysis-related claims")
            data_refs.append(DataReference(
                source_file="claims_professional.csv",
                row_indices=esrd_claims_by_member.get(member_id, []),
                columns_used=["claim_id", "diagnosis_code_1", "procedure_code"],
                description=f"ESRD with dialysis on {len(esrd_claims_by_member.get(member_id, []))} claim(s)",
            ))

        # Check service area
        if service_area_required:
            member_zip = str(member.get("zip_code", ""))
            if member_zip and member_zip not in service_area_zips:
                reasons_excluded.append(
                    f"Member ZIP {member_zip} is outside ACO service area"
                )

        # Check deceased before performance year
        deceased_date = member.get("deceased_date")
        if pd.notna(deceased_date) and deceased_date < perf_start:
            reasons_excluded.append(
                f"Member deceased before performance year ({deceased_date.date()})"
            )

        if reasons_excluded:
            outcome = "excluded"
            reason = "; ".join(reasons_excluded)
        else:
            outcome = "eligible"
            reason = f"Enrolled {enrollment_months} month(s), no exclusions apply"
            eligible_member_ids.append(member_id)

        member_details.append(MemberDetail(
            member_id=member_id,
            outcome=outcome,
            reason=reason,
            data_references=data_refs,
            intermediate_values={
                "enrollment_months": enrollment_months,
                "exclusions_triggered": reasons_excluded,
            },
        ))

    src_lines = inspect.getsourcelines(determine_eligibility)
    start_line = src_lines[1]
    end_line = start_line + len(src_lines[0]) - 1
    code_ref = CodeReference(
        module="step_1_eligibility",
        function="determine_eligibility",
        line_range=(start_line, end_line),
        logic_summary=(
            "Load eligibility records for each member. Calculate months of enrollment "
            "during the performance year. Apply exclusions: ESRD (dialysis claims with N18.6), "
            "out-of-service-area (ZIP code check), deceased before performance year. "
            "Members passing all checks are marked eligible for attribution."
        ),
    )

    excluded_count = len(members) - len(eligible_member_ids)
    elapsed_ms = int((time.time() - start) * 1000)

    return StepResult(
        step_name="eligibility",
        step_number=1,
        contract_clauses=[contract_clause],
        code_references=[code_ref],
        summary={
            "total_members": len(members),
            "eligible_count": len(eligible_member_ids),
            "excluded_count": excluded_count,
            "eligible_member_ids": eligible_member_ids,
        },
        member_details=member_details,
        data_quality_flags=data_quality_flags,
        execution_time_ms=elapsed_ms,
    )


def _calc_all_enrollment_months(
    eligibility: pd.DataFrame,
    perf_start: pd.Timestamp,
    perf_end: pd.Timestamp,
) -> dict[str, int]:
    """Calculate enrollment months for all members at once."""
    result = {}
    for mid, group in eligibility.groupby("member_id"):
        months = set()
        for _, row in group.iterrows():
            start = row["enrollment_start_date"]
            end = row["enrollment_end_date"]
            if pd.isna(start):
                continue
            if pd.isna(end):
                end = perf_end
            ps = max(start, perf_start)
            pe = min(end, perf_end)
            if ps > pe:
                continue
            current = ps.replace(day=1)
            while current <= pe:
                months.add(current.month)
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        result[mid] = len(months)
    return result
