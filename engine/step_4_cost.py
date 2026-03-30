"""Step 4: Cost and PMPM Calculation with claims maturity adjustments.

Contract clause (COST-1.0):
    "Total cost of care shall be calculated as the sum of all Parts A and B
     allowed charges for attributed beneficiaries during the performance year,
     divided by the number of attributed beneficiary-months, expressed as a
     per-member-per-month (PMPM) amount."
"""

import inspect
import time
from collections import defaultdict

import pandas as pd

from engine.data_loader import LoadedData
from engine.provenance import (
    CodeReference,
    ContractClause,
    DataReference,
    MemberDetail,
    StepResult,
)

# Empirical run-out curve: fraction of claims received by months after service
RUNOUT_CURVE = {
    0: 0.40,
    1: 0.82,
    2: 0.92,
    3: 0.96,
    4: 0.98,
    5: 0.99,
    6: 0.99,
    9: 1.00,
    12: 1.00,
}


def _get_maturity_factor(months_lag: int) -> float:
    """Get the claims maturity factor for a given month lag."""
    if months_lag >= 12:
        return 1.0
    # Find the closest key
    keys = sorted(RUNOUT_CURVE.keys())
    for k in keys:
        if months_lag <= k:
            return RUNOUT_CURVE[k]
    return 1.0


def calculate_cost(
    data: LoadedData,
    contract: dict,
    attribution_result: StepResult,
) -> StepResult:
    """Calculate PMPM cost with maturity adjustments."""
    start = time.time()

    cost_clause = contract["clauses"]["cost_calculation"]
    params = cost_clause["parameters"]
    cost_basis = params.get("cost_basis", "allowed_amount")
    include_pharmacy = params.get("include_pharmacy", False)
    runout_months = params.get("runout_months", 3)

    contract_clause = ContractClause(
        clause_id=cost_clause["clause_id"],
        clause_text=cost_clause["text"],
        interpretation=(
            f"Calculate total cost using {cost_basis.replace('_', ' ')} as the cost basis. "
            f"{'Including' if include_pharmacy else 'Excluding'} pharmacy claims. "
            f"Claims run-out window: {runout_months} months after performance year end."
        ),
        parameters_extracted=params,
    )

    attributed_ids = set(attribution_result.summary.get("attributed_population", []))
    perf_year = contract.get("performance_year", 2025)
    perf_start = pd.Timestamp(f"{perf_year}-01-01")
    perf_end = pd.Timestamp(f"{perf_year}-12-31")
    # data_as_of_date simulates mid-year snapshot
    data_as_of = pd.Timestamp("2025-10-15")

    # Calculate member-months from eligibility
    eligibility = data.eligibility
    member_months = _calc_member_months(eligibility, attributed_ids, perf_start, perf_end)
    total_member_months = sum(member_months.values())

    # Gather costs from professional + facility claims (+ pharmacy if enabled)
    claims_pro = data.claims_professional
    claims_fac = data.claims_facility

    # Filter to attributed members, performance year, paid claims
    pro_filtered = claims_pro[
        (claims_pro["member_id"].isin(attributed_ids)) &
        (claims_pro["service_date"] >= perf_start) &
        (claims_pro["service_date"] <= perf_end) &
        (claims_pro["claim_status"] == "paid")
    ].copy()

    fac_filtered = claims_fac[
        (claims_fac["member_id"].isin(attributed_ids)) &
        (claims_fac["service_date"] >= perf_start) &
        (claims_fac["service_date"] <= perf_end) &
        (claims_fac["claim_status"] == "paid")
    ].copy()

    # Categorize costs
    cost_col = cost_basis  # "allowed_amount" or "paid_amount"

    # Professional costs by category
    pro_total = pro_filtered[cost_col].sum()
    fac_total = fac_filtered[cost_col].sum()

    rx_total = 0.0
    rx_filtered = pd.DataFrame()
    if include_pharmacy:
        rx_filtered = data.claims_pharmacy[
            (data.claims_pharmacy["member_id"].isin(attributed_ids)) &
            (data.claims_pharmacy["fill_date"] >= perf_start) &
            (data.claims_pharmacy["fill_date"] <= perf_end)
        ].copy()
        rx_total = rx_filtered[cost_col].sum()

    raw_total = pro_total + fac_total + rx_total
    raw_pmpm = raw_total / total_member_months if total_member_months > 0 else 0.0

    # Apply maturity adjustments by month
    monthly_costs, monthly_adjustments = _apply_maturity_adjustments(
        pro_filtered, fac_filtered, rx_filtered if include_pharmacy else pd.DataFrame(),
        cost_col, data_as_of, perf_start, perf_end,
    )

    adjusted_total = sum(m["adjusted_cost"] for m in monthly_adjustments.values())
    adjusted_pmpm = adjusted_total / total_member_months if total_member_months > 0 else 0.0

    # Confidence band based on maturity uncertainty
    uncertainty = sum(
        m["adjusted_cost"] - m["raw_cost"]
        for m in monthly_adjustments.values()
    )
    pmpm_low = raw_pmpm
    pmpm_high = adjusted_pmpm + (uncertainty / total_member_months if total_member_months > 0 else 0)

    # Per-member cost details (top 20 by cost, vectorized)
    member_costs = defaultdict(float)
    pro_by_member = pro_filtered.groupby("member_id")[cost_col].sum()
    for mid, cost_val in pro_by_member.items():
        member_costs[mid] += cost_val
    fac_by_member = fac_filtered.groupby("member_id")[cost_col].sum()
    for mid, cost_val in fac_by_member.items():
        member_costs[mid] += cost_val
    if include_pharmacy and not rx_filtered.empty:
        rx_by_member = rx_filtered.groupby("member_id")[cost_col].sum()
        for mid, cost_val in rx_by_member.items():
            member_costs[mid] += cost_val

    top_members = sorted(member_costs.items(), key=lambda x: x[1], reverse=True)[:20]

    member_details = []
    for mid, cost in top_members:
        mm = member_months.get(mid, 0)
        member_pmpm = cost / mm if mm > 0 else 0
        pro_claims = pro_filtered[pro_filtered["member_id"] == mid]
        fac_claims = fac_filtered[fac_filtered["member_id"] == mid]

        refs = []
        if not pro_claims.empty:
            refs.append(DataReference(
                source_file="claims_professional.csv",
                row_indices=pro_claims.index.tolist()[:10],
                columns_used=["claim_id", "member_id", cost_col, "service_date"],
                description=f"{len(pro_claims)} professional claims, ${pro_claims[cost_col].sum():,.2f}",
            ))
        if not fac_claims.empty:
            refs.append(DataReference(
                source_file="claims_facility.csv",
                row_indices=fac_claims.index.tolist()[:10],
                columns_used=["claim_id", "member_id", cost_col, "service_date"],
                description=f"{len(fac_claims)} facility claims, ${fac_claims[cost_col].sum():,.2f}",
            ))

        member_details.append(MemberDetail(
            member_id=mid,
            outcome="costed",
            reason=f"Total cost: ${cost:,.2f}, PMPM: ${member_pmpm:,.2f} ({mm} member-months)",
            data_references=refs,
            intermediate_values={
                "total_cost": round(cost, 2),
                "member_months": mm,
                "member_pmpm": round(member_pmpm, 2),
            },
        ))

    src_lines = inspect.getsourcelines(calculate_cost)
    start_line = src_lines[1]
    end_line = start_line + len(src_lines[0]) - 1

    elapsed_ms = int((time.time() - start) * 1000)

    return StepResult(
        step_name="cost",
        step_number=4,
        contract_clauses=[contract_clause],
        code_references=[CodeReference(
            module="step_4_cost",
            function="calculate_cost",
            line_range=(start_line, end_line),
            logic_summary=(
                "Sum allowed amounts for attributed members' paid claims during the "
                "performance year. Calculate member-months from eligibility. "
                "Apply claims maturity adjustment for incomplete months. "
                "Compute raw and adjusted PMPM with confidence bands."
            ),
        )],
        summary={
            "total_member_months": total_member_months,
            "raw_total_cost": round(raw_total, 2),
            "adjusted_total_cost": round(adjusted_total, 2),
            "raw_pmpm": round(raw_pmpm, 2),
            "actual_pmpm": round(adjusted_pmpm, 2),
            "pmpm_confidence_low": round(pmpm_low, 2),
            "pmpm_confidence_high": round(pmpm_high, 2),
            "cost_by_category": {
                "professional": round(pro_total, 2),
                "facility": round(fac_total, 2),
                "pharmacy": round(rx_total, 2),
            },
            "monthly_maturity": {
                str(k): {
                    "raw_cost": round(v["raw_cost"], 2),
                    "maturity_factor": v["maturity_factor"],
                    "adjusted_cost": round(v["adjusted_cost"], 2),
                }
                for k, v in monthly_adjustments.items()
            },
            "attributed_count": len(attributed_ids),
        },
        member_details=member_details,
        execution_time_ms=elapsed_ms,
    )


def _calc_member_months(
    eligibility: pd.DataFrame,
    attributed_ids: set[str],
    perf_start: pd.Timestamp,
    perf_end: pd.Timestamp,
) -> dict[str, int]:
    """Calculate member-months for each attributed member."""
    result = {}
    for mid in attributed_ids:
        member_elig = eligibility[eligibility["member_id"] == mid]
        months = set()
        for _, row in member_elig.iterrows():
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
                months.add((current.year, current.month))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
        result[mid] = len(months)
    return result


def _apply_maturity_adjustments(
    pro_claims: pd.DataFrame,
    fac_claims: pd.DataFrame,
    rx_claims: pd.DataFrame,
    cost_col: str,
    data_as_of: pd.Timestamp,
    perf_start: pd.Timestamp,
    perf_end: pd.Timestamp,
) -> tuple[dict, dict]:
    """Apply claims maturity adjustments by service month (vectorized)."""
    monthly_raw = defaultdict(float)

    for df, date_col in [(pro_claims, "service_date"), (fac_claims, "service_date"), (rx_claims, "fill_date")]:
        if df.empty:
            continue
        valid = df[[date_col, cost_col]].dropna(subset=[date_col])
        valid = valid.copy()
        valid["_month_key"] = valid[date_col].dt.to_period("M")
        monthly = valid.groupby("_month_key")[cost_col].sum()
        for period, total in monthly.items():
            monthly_raw[(period.year, period.month)] += total

    monthly_adjustments = {}
    for month_key in sorted(monthly_raw.keys()):
        year, month = month_key
        months_lag = (data_as_of.year - year) * 12 + (data_as_of.month - month)
        maturity = _get_maturity_factor(months_lag)
        raw = monthly_raw[month_key]
        adjusted = raw / maturity if maturity > 0 else raw

        monthly_adjustments[month_key] = {
            "raw_cost": raw,
            "maturity_factor": maturity,
            "adjusted_cost": adjusted,
            "months_lag": months_lag,
        }

    return monthly_raw, monthly_adjustments
