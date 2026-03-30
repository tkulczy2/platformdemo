"""Step 6: Reconciliation — compare platform calculations to payer settlement report.

Independently discovers discrepancies between the platform's calculation and
the payer's reported values. Does NOT read the discrepancy manifest.
"""

import inspect
import time

from engine.data_loader import LoadedData
from engine.provenance import (
    CodeReference,
    ContractClause,
    DataReference,
    MemberDetail,
    StepResult,
)


def reconcile(
    steps: list[StepResult],
    payer_report: dict,
    data: LoadedData,
) -> dict:
    """Compare platform results to payer settlement report."""
    start = time.time()

    # Extract platform results from pipeline steps
    platform = _extract_platform_results(steps)

    payer_attr = payer_report.get("attribution", {})
    payer_qual = payer_report.get("quality", {})
    payer_cost = payer_report.get("cost", {})

    discrepancies = []

    # --- Attribution discrepancies ---
    platform_attributed = set(platform.get("attributed_population", []))
    payer_attributed_count = payer_attr.get("total_attributed", 0)
    platform_attributed_count = len(platform_attributed)

    if platform_attributed_count != payer_attributed_count:
        diff = platform_attributed_count - payer_attributed_count
        discrepancies.append({
            "category": "data_difference" if abs(diff) > 5 else "methodology_difference",
            "metric": "attribution_count",
            "platform_value": platform_attributed_count,
            "payer_value": payer_attributed_count,
            "difference": diff,
            "financial_impact": _estimate_attribution_impact(
                diff, platform.get("actual_pmpm", 0), platform.get("benchmark_pmpm", 1187.0)
            ),
            "explanation": (
                f"Platform attributes {platform_attributed_count} members vs payer's "
                f"{payer_attributed_count} ({'+' if diff > 0 else ''}{diff}). "
                f"Differences likely due to claims run-out timing, provider roster "
                f"effective dates, and tiebreaker methodology."
            ),
            "resolution_recommendation": (
                "Review member-level attribution lists side by side. "
                "Identify members attributed by one party but not the other. "
                "Check for late-arriving claims and provider termination dates."
            ),
        })

    # --- Quality measure discrepancies ---
    payer_measures = payer_qual.get("measures", {})
    platform_measures = platform.get("measures", {})

    for measure_key, payer_measure in payer_measures.items():
        platform_measure = platform_measures.get(measure_key, {})
        if not platform_measure:
            continue

        payer_rate = payer_measure.get("rate", 0)
        platform_rate = platform_measure.get("rate", 0)
        rate_diff = platform_rate - payer_rate

        if abs(rate_diff) > 0.5:  # More than 0.5 percentage point difference
            payer_num = payer_measure.get("numerator", 0)
            platform_num = platform_measure.get("numerator_count", 0)
            payer_denom = payer_measure.get("denominator", 0)
            platform_denom = platform_measure.get("eligible_count", 0)

            # Determine category
            if abs(platform_denom - payer_denom) > 3:
                category = "methodology_difference"
                explanation_detail = (
                    f"Denominator difference: platform has {platform_denom}, "
                    f"payer has {payer_denom}. May be due to different exclusion criteria."
                )
            elif abs(platform_num - payer_num) > 2:
                category = "data_difference"
                explanation_detail = (
                    f"Numerator difference: platform has {platform_num}, "
                    f"payer has {payer_num}. Platform may be using EHR data "
                    f"(lab results, screening records) not available to payer."
                )
            else:
                category = "specification_ambiguity"
                explanation_detail = "Small differences in rate calculation methodology."

            discrepancies.append({
                "category": category,
                "metric": f"quality_{measure_key}",
                "platform_value": platform_rate,
                "payer_value": payer_rate,
                "difference": round(rate_diff, 2),
                "financial_impact": _estimate_quality_impact(
                    rate_diff,
                    platform.get("gross_savings", 0),
                    platform.get("quality_composite", 0),
                    platform.get("quality_gate_threshold", 0.40),
                ),
                "explanation": (
                    f"{measure_key}: Platform rate {platform_rate:.1f}% vs payer "
                    f"{payer_rate:.1f}% (Δ{rate_diff:+.1f}pp). {explanation_detail}"
                ),
                "resolution_recommendation": (
                    "Compare member-level measure results. Identify members "
                    "where platform and payer disagree on numerator/denominator status. "
                    "Check for EHR-only data and claims-only exclusions."
                ),
                "detail": {
                    "platform_numerator": platform_num,
                    "payer_numerator": payer_num,
                    "platform_denominator": platform_denom,
                    "payer_denominator": payer_denom,
                },
            })

    # --- Cost discrepancies ---
    payer_pmpm = payer_cost.get("actual_pmpm", 0)
    platform_pmpm = platform.get("actual_pmpm", 0)
    pmpm_diff = platform_pmpm - payer_pmpm

    if abs(pmpm_diff) > 1.0:  # More than $1 PMPM difference
        total_mm = platform.get("total_member_months", 0)
        cost_impact = pmpm_diff * total_mm

        discrepancies.append({
            "category": "timing_difference",
            "metric": "actual_pmpm",
            "platform_value": platform_pmpm,
            "payer_value": payer_pmpm,
            "difference": round(pmpm_diff, 2),
            "financial_impact": round(cost_impact, 2),
            "explanation": (
                f"PMPM: Platform ${platform_pmpm:,.2f} vs payer ${payer_pmpm:,.2f} "
                f"(Δ${pmpm_diff:+,.2f}). Likely due to claims run-out timing differences "
                f"and maturity adjustments. Total impact: ${cost_impact:,.2f}."
            ),
            "resolution_recommendation": (
                "Compare claims included in each calculation. "
                "Check for claims adjudicated after payer's cutoff date. "
                "Review maturity adjustment methodology."
            ),
        })

    # Settlement comparison
    payer_savings = payer_cost.get("shared_savings_amount", 0)
    platform_savings = platform.get("shared_savings_amount", 0)
    savings_diff = platform_savings - payer_savings

    if abs(savings_diff) > 100:  # More than $100 difference
        discrepancies.append({
            "category": "methodology_difference",
            "metric": "shared_savings_amount",
            "platform_value": platform_savings,
            "payer_value": payer_savings,
            "difference": round(savings_diff, 2),
            "financial_impact": round(savings_diff, 2),
            "explanation": (
                f"Shared savings: Platform ${platform_savings:,.2f} vs payer "
                f"${payer_savings:,.2f} (Δ${savings_diff:+,.2f}). "
                f"This is a downstream effect of attribution, quality, and cost differences."
            ),
            "resolution_recommendation": (
                "Resolve upstream discrepancies (attribution, quality, cost) first. "
                "The settlement difference is a consequence of those inputs."
            ),
        })

    total_financial_impact = sum(abs(d.get("financial_impact", 0)) for d in discrepancies)

    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "discrepancies": discrepancies,
        "total_financial_impact": round(total_financial_impact, 2),
        "discrepancy_count": len(discrepancies),
        "categories": _summarize_by_category(discrepancies),
        "execution_time_ms": elapsed_ms,
    }


def _extract_platform_results(steps: list[StepResult]) -> dict:
    """Extract key metrics from pipeline steps for comparison."""
    result = {}
    for step in steps:
        if step.step_name == "attribution":
            result["attributed_population"] = step.summary.get("attributed_population", [])
            result["attributed_count"] = step.summary.get("attributed_count", 0)
        elif step.step_name == "quality":
            result["quality_composite"] = step.summary.get("composite_score", 0)
            result["measures"] = step.summary.get("measures", {})
        elif step.step_name == "cost":
            result["actual_pmpm"] = step.summary.get("actual_pmpm", 0)
            result["total_member_months"] = step.summary.get("total_member_months", 0)
        elif step.step_name == "settlement":
            result["benchmark_pmpm"] = step.summary.get("benchmark_pmpm", 1187.0)
            result["gross_savings"] = step.summary.get("gross_savings", 0)
            result["shared_savings_amount"] = step.summary.get("shared_savings_amount", 0)
            result["quality_gate_threshold"] = step.summary.get("quality_gate_threshold", 0.40)
    return result


def _estimate_attribution_impact(
    member_diff: int,
    actual_pmpm: float,
    benchmark_pmpm: float,
) -> float:
    """Estimate financial impact of attribution count difference."""
    # Each additional member changes the total cost and benchmark
    savings_per_member_per_month = benchmark_pmpm - actual_pmpm
    # Assume average 10 months enrollment
    return round(abs(member_diff) * savings_per_member_per_month * 10, 2)


def _estimate_quality_impact(
    rate_diff: float,
    gross_savings: float,
    quality_composite: float,
    quality_gate: float,
) -> float:
    """Estimate financial impact of quality measure discrepancy."""
    # Quality affects whether the gate is passed and the savings multiplier
    # Simplified: if quality change could flip the gate, impact = full savings
    if quality_composite / 100.0 < quality_gate + 0.05:
        return abs(gross_savings * 0.1)  # Near the gate threshold
    return 0.0


def _summarize_by_category(discrepancies: list[dict]) -> dict:
    """Summarize discrepancies by category."""
    summary = {}
    for d in discrepancies:
        cat = d.get("category", "unknown")
        if cat not in summary:
            summary[cat] = {"count": 0, "total_impact": 0.0}
        summary[cat]["count"] += 1
        summary[cat]["total_impact"] += abs(d.get("financial_impact", 0))
    return summary
