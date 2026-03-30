"""Step 2: Attribution — MSSP two-step plurality attribution.

Contract clauses:
    ATTR-1.1: "Step 1: Assign each eligible beneficiary to the ACO participant
               (TIN/NPI) that provided the plurality of primary care services..."
    ATTR-1.2: "Step 2: For beneficiaries not assigned in Step 1, assign based on
               the plurality of primary care services provided by any ACO participant..."
    ATTR-1.3: "In the event of a tie in service counts, the beneficiary shall be
               assigned to the provider whose most recent qualifying service was
               most recent in time."
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


def assign_attribution(
    data: LoadedData,
    contract: dict,
    eligibility_result: StepResult,
) -> StepResult:
    """Assign each eligible member to a provider using two-step plurality attribution."""
    start = time.time()

    clauses = contract["clauses"]
    step1_clause = clauses["attribution_step1"]
    step2_clause = clauses["attribution_step2"]
    tie_clause = clauses["attribution_tiebreaker"]

    qualifying_codes = set(step1_clause["parameters"]["qualifying_cpt_codes"])
    provider_filter_step1 = step1_clause["parameters"].get("provider_filter_step1", "pcp_only")
    tiebreaker = tie_clause["parameters"].get("tiebreaker", "most_recent_visit")

    contract_clauses = [
        ContractClause(
            clause_id=step1_clause["clause_id"],
            clause_text=step1_clause["text"],
            interpretation=(
                f"Filter professional claims to qualifying CPT codes "
                f"({len(qualifying_codes)} codes). In Step 1, consider only "
                f"{'PCP providers' if provider_filter_step1 == 'pcp_only' else 'all ACO participants'}. "
                f"Assign member to provider with most qualifying visits (plurality)."
            ),
            parameters_extracted=step1_clause["parameters"],
        ),
        ContractClause(
            clause_id=step2_clause["clause_id"],
            clause_text=step2_clause["text"],
            interpretation=(
                "For members not attributed in Step 1, expand the provider pool "
                "to all ACO participants including specialists."
            ),
            parameters_extracted=step2_clause["parameters"],
        ),
        ContractClause(
            clause_id=tie_clause["clause_id"],
            clause_text=tie_clause["text"],
            interpretation=(
                f"Tiebreaker method: {tiebreaker.replace('_', ' ')}. "
                "When two providers have equal qualifying visit counts, "
                "the tie is broken by the most recent qualifying service date."
            ),
            parameters_extracted=tie_clause["parameters"],
        ),
    ]

    eligible_ids = set(eligibility_result.summary["eligible_member_ids"])

    providers = data.providers
    claims = data.claims_professional
    perf_year = contract.get("performance_year", 2025)
    perf_start = pd.Timestamp(f"{perf_year}-01-01")
    perf_end = pd.Timestamp(f"{perf_year}-12-31")

    # Build provider lookup sets
    active_providers = providers[
        (providers["aco_participant"] == True) &
        (providers["effective_date"] <= perf_end) &
        (providers["termination_date"].isna() | (providers["termination_date"] >= perf_start))
    ]
    pcp_npis = set(active_providers[active_providers["is_pcp"] == True]["npi"])
    all_aco_npis = set(active_providers["npi"])
    provider_names = dict(zip(providers["npi"], providers["provider_name"]))

    # Filter claims to qualifying codes within performance year (vectorized)
    qualifying_claims = claims[
        (claims["member_id"].isin(eligible_ids)) &
        (claims["procedure_code"].isin(qualifying_codes)) &
        (claims["service_date"] >= perf_start) &
        (claims["service_date"] <= perf_end) &
        (claims["claim_status"] != "denied") &
        (claims["rendering_npi"].notna())
    ].copy()

    # Vectorized: count visits by (member, provider) and get most recent date
    if not qualifying_claims.empty:
        visit_stats = qualifying_claims.groupby(["member_id", "rendering_npi"]).agg(
            visit_count=("claim_id", "count"),
            most_recent=("service_date", "max"),
        ).reset_index()
    else:
        visit_stats = pd.DataFrame(columns=["member_id", "rendering_npi", "visit_count", "most_recent"])

    # Pre-compute claim indices per member
    claim_indices_by_member = {}
    if not qualifying_claims.empty:
        for mid, group in qualifying_claims.groupby("member_id"):
            claim_indices_by_member[mid] = group.index.tolist()

    member_details = []
    attributed_members = {}
    step1_attributed = 0
    step2_attributed = 0
    unattributed = 0

    # Process each eligible member
    for member_id in eligible_ids:
        member_visits = visit_stats[visit_stats["member_id"] == member_id]

        if member_visits.empty:
            member_details.append(MemberDetail(
                member_id=member_id,
                outcome="unattributed",
                reason="No qualifying E&M visits found during the performance year",
                data_references=[DataReference(
                    source_file="claims_professional.csv",
                    row_indices=[],
                    columns_used=["member_id", "procedure_code", "rendering_npi"],
                    description="No qualifying claims found",
                )],
                intermediate_values={"qualifying_visit_count": 0},
            ))
            unattributed += 1
            continue

        visit_count_dict = {
            row["rendering_npi"]: {
                "count": int(row["visit_count"]),
                "most_recent": str(row["most_recent"].date()) if pd.notna(row["most_recent"]) else "",
            }
            for _, row in member_visits.iterrows()
        }

        # Step 1: PCP providers only
        step1_visits = member_visits[member_visits["rendering_npi"].isin(pcp_npis)]
        attributed_npi, attr_step = _find_plurality_provider(step1_visits, tiebreaker, "step1")

        # Step 2: All ACO providers
        if attributed_npi is None:
            step2_visits = member_visits[member_visits["rendering_npi"].isin(all_aco_npis)]
            attributed_npi, attr_step = _find_plurality_provider(step2_visits, tiebreaker, "step2")

        claim_indices = claim_indices_by_member.get(member_id, [])

        if attributed_npi:
            provider_name = provider_names.get(attributed_npi, "Unknown")
            visit_info = visit_count_dict.get(attributed_npi, {"count": 0})

            if attr_step == "step1":
                step1_attributed += 1
            else:
                step2_attributed += 1

            attributed_members[member_id] = {
                "npi": attributed_npi,
                "provider_name": provider_name,
                "step": attr_step,
                "visit_count": visit_info["count"],
            }

            member_details.append(MemberDetail(
                member_id=member_id,
                outcome="attributed",
                reason=(
                    f"Attributed to {provider_name} (NPI: {attributed_npi}) via {attr_step} — "
                    f"{visit_info['count']} qualifying visit(s)"
                ),
                data_references=[DataReference(
                    source_file="claims_professional.csv",
                    row_indices=claim_indices[:20],
                    columns_used=["claim_id", "member_id", "rendering_npi", "procedure_code", "service_date"],
                    description=f"{len(claim_indices)} qualifying claims across {len(member_visits)} provider(s)",
                )],
                intermediate_values={
                    "visit_counts_by_provider": visit_count_dict,
                    "attributed_npi": attributed_npi,
                    "attribution_step": attr_step,
                },
            ))
        else:
            unattributed += 1
            member_details.append(MemberDetail(
                member_id=member_id,
                outcome="unattributed",
                reason="Qualifying visits found but none from active ACO participants",
                data_references=[DataReference(
                    source_file="claims_professional.csv",
                    row_indices=claim_indices[:20],
                    columns_used=["claim_id", "member_id", "rendering_npi", "procedure_code"],
                    description=f"{len(claim_indices)} qualifying claims, none from ACO providers",
                )],
                intermediate_values={"visit_counts_by_provider": visit_count_dict},
            ))

    src_lines = inspect.getsourcelines(assign_attribution)
    start_line = src_lines[1]
    end_line = start_line + len(src_lines[0]) - 1

    elapsed_ms = int((time.time() - start) * 1000)

    return StepResult(
        step_name="attribution",
        step_number=2,
        contract_clauses=contract_clauses,
        code_references=[CodeReference(
            module="step_2_attribution",
            function="assign_attribution",
            line_range=(start_line, end_line),
            logic_summary=(
                "Filter claims to qualifying E&M/wellness CPT codes. "
                "Step 1: Count qualifying visits per PCP provider, assign to plurality winner. "
                "Step 2: For unassigned members, expand to all ACO providers. "
                "Tiebreaker: most recent qualifying visit date."
            ),
        )],
        summary={
            "total_eligible": len(eligible_ids),
            "attributed_count": step1_attributed + step2_attributed,
            "attributed_step1": step1_attributed,
            "attributed_step2": step2_attributed,
            "unattributed_count": unattributed,
            "attributed_population": list(attributed_members.keys()),
            "attribution_details": attributed_members,
        },
        member_details=member_details,
        execution_time_ms=elapsed_ms,
    )


def _find_plurality_provider(
    visit_counts: pd.DataFrame,
    tiebreaker: str,
    step_label: str,
) -> tuple[str | None, str]:
    """Find the provider with the most visits, applying tiebreaker if needed."""
    if visit_counts.empty:
        return None, step_label

    max_visits = visit_counts["visit_count"].max()
    top_providers = visit_counts[visit_counts["visit_count"] == max_visits]

    if len(top_providers) == 1:
        return top_providers.iloc[0]["rendering_npi"], step_label

    if tiebreaker == "most_recent_visit":
        top_providers = top_providers.sort_values("most_recent", ascending=False)
    elif tiebreaker == "alphabetical_npi":
        top_providers = top_providers.sort_values("rendering_npi")

    return top_providers.iloc[0]["rendering_npi"], step_label
