"""Step 5: Settlement Calculation — benchmark comparison, gates, and savings.

Contract clauses:
    SETTLE-1.0: Benchmark of $1,187.00 PMPM, 2% MSR, 50% shared savings rate
    SETTLE-1.1: Quality gate requires 40% composite score minimum
"""

import inspect
import time

from engine.provenance import (
    CodeReference,
    ContractClause,
    MemberDetail,
    StepResult,
)


def calculate_settlement(
    contract: dict,
    quality_result: StepResult,
    cost_result: StepResult,
) -> StepResult:
    """Calculate settlement: benchmark vs actual, gates, shared savings."""
    start = time.time()

    settle_clause = contract["clauses"]["settlement"]
    gate_clause = contract["clauses"]["quality_gate"]
    settle_params = settle_clause["parameters"]
    gate_params = gate_clause["parameters"]

    benchmark_pmpm = settle_params.get("benchmark_pmpm", 1187.00)
    msr = settle_params.get("minimum_savings_rate", 0.02)
    shared_rate = settle_params.get("shared_savings_rate", 0.50)
    quality_gate = gate_params.get("quality_gate_threshold", 0.40)

    contract_clauses = [
        ContractClause(
            clause_id=settle_clause["clause_id"],
            clause_text=settle_clause["text"],
            interpretation=(
                f"Benchmark PMPM: ${benchmark_pmpm:,.2f}. "
                f"Minimum savings rate: {msr:.1%}. "
                f"Shared savings rate: {shared_rate:.0%}."
            ),
            parameters_extracted=settle_params,
        ),
        ContractClause(
            clause_id=gate_clause["clause_id"],
            clause_text=gate_clause["text"],
            interpretation=(
                f"Quality gate: composite score must exceed {quality_gate:.0%} "
                f"for the ACO to be eligible for shared savings."
            ),
            parameters_extracted=gate_params,
        ),
    ]

    # Pull values from prior steps
    actual_pmpm = cost_result.summary.get("actual_pmpm", 0)
    total_member_months = cost_result.summary.get("total_member_months", 0)
    quality_composite = quality_result.summary.get("composite_score", 0)
    pmpm_low = cost_result.summary.get("pmpm_confidence_low", actual_pmpm)
    pmpm_high = cost_result.summary.get("pmpm_confidence_high", actual_pmpm)

    # Calculate settlement
    total_benchmark = benchmark_pmpm * total_member_months
    total_actual = actual_pmpm * total_member_months
    gross_savings = total_benchmark - total_actual

    savings_rate = (benchmark_pmpm - actual_pmpm) / benchmark_pmpm if benchmark_pmpm > 0 else 0
    msr_passed = savings_rate > msr
    quality_gate_passed = (quality_composite / 100.0) > quality_gate

    if msr_passed and quality_gate_passed:
        shared_savings = gross_savings * shared_rate
        settlement_status = "eligible"
    else:
        shared_savings = 0.0
        settlement_status = "ineligible"

    # Confidence range for savings
    gross_savings_low = (benchmark_pmpm - pmpm_high) * total_member_months
    gross_savings_high = (benchmark_pmpm - pmpm_low) * total_member_months
    shared_savings_low = max(0, gross_savings_low * shared_rate) if msr_passed and quality_gate_passed else 0
    shared_savings_high = max(0, gross_savings_high * shared_rate) if msr_passed and quality_gate_passed else 0

    member_details = [
        MemberDetail(
            member_id="ACO-LEVEL",
            outcome=settlement_status,
            reason=(
                f"Benchmark: ${benchmark_pmpm:,.2f}, Actual: ${actual_pmpm:,.2f}, "
                f"Savings rate: {savings_rate:.2%}. "
                f"MSR ({msr:.1%}): {'PASSED' if msr_passed else 'FAILED'}. "
                f"Quality gate ({quality_gate:.0%}): {'PASSED' if quality_gate_passed else 'FAILED'}. "
                f"Shared savings: ${shared_savings:,.2f}"
            ),
            intermediate_values={
                "benchmark_pmpm": benchmark_pmpm,
                "actual_pmpm": actual_pmpm,
                "savings_rate": round(savings_rate, 4),
                "msr_passed": msr_passed,
                "quality_composite": quality_composite,
                "quality_gate_passed": quality_gate_passed,
            },
        ),
    ]

    src_lines = inspect.getsourcelines(calculate_settlement)
    start_line = src_lines[1]
    end_line = start_line + len(src_lines[0]) - 1

    elapsed_ms = int((time.time() - start) * 1000)

    return StepResult(
        step_name="settlement",
        step_number=5,
        contract_clauses=contract_clauses,
        code_references=[CodeReference(
            module="step_5_settlement",
            function="calculate_settlement",
            line_range=(start_line, end_line),
            logic_summary=(
                "Compare actual PMPM to benchmark. Check minimum savings rate (MSR) "
                "and quality gate. If both pass, calculate shared savings = "
                "gross savings × shared savings rate."
            ),
        )],
        summary={
            "benchmark_pmpm": benchmark_pmpm,
            "actual_pmpm": actual_pmpm,
            "total_benchmark": round(total_benchmark, 2),
            "total_actual": round(total_actual, 2),
            "gross_savings": round(gross_savings, 2),
            "savings_rate": round(savings_rate, 4),
            "msr_threshold": msr,
            "msr_passed": msr_passed,
            "quality_composite": quality_composite,
            "quality_gate_threshold": quality_gate,
            "quality_gate_passed": quality_gate_passed,
            "shared_savings_rate": shared_rate,
            "shared_savings_amount": round(shared_savings, 2),
            "settlement_status": settlement_status,
            "confidence_range": {
                "shared_savings_low": round(shared_savings_low, 2),
                "shared_savings_high": round(shared_savings_high, 2),
            },
            "total_member_months": total_member_months,
        },
        member_details=member_details,
        execution_time_ms=elapsed_ms,
    )
