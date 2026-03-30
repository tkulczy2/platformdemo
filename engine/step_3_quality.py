"""Step 3: Quality Measure Calculation — orchestrates all measures and computes composite.

Runs each quality measure, computes weighted composite score, and produces
a unified StepResult with all measure details.
"""

import inspect
import time

from engine.data_loader import LoadedData
from engine.measures.blood_pressure import BloodPressureControl
from engine.measures.breast_cancer_screening import BreastCancerScreening
from engine.measures.colorectal_screening import ColorectalScreening
from engine.measures.depression_screening import DepressionScreening
from engine.measures.hba1c_control import HbA1cPoorControl
from engine.provenance import (
    CodeReference,
    ContractClause,
    MemberDetail,
    StepResult,
)

# Registry of all available measures
MEASURE_REGISTRY = {
    "hba1c_poor_control": HbA1cPoorControl,
    "controlling_bp": BloodPressureControl,
    "breast_cancer_screening": BreastCancerScreening,
    "colorectal_screening": ColorectalScreening,
    "depression_screening": DepressionScreening,
}


def calculate_quality_measures(
    data: LoadedData,
    contract: dict,
    attribution_result: StepResult,
) -> StepResult:
    """Calculate all quality measures and produce composite score."""
    start = time.time()

    qual_clause = contract["clauses"]["quality_measures"]
    params = qual_clause["parameters"]
    enabled_measures = params.get("measures", list(MEASURE_REGISTRY.keys()))
    weights = params.get("measure_weights", {})
    conflict_resolution = params.get("conflict_resolution", "most_recent_clinical")

    contract_clause = ContractClause(
        clause_id=qual_clause["clause_id"],
        clause_text=qual_clause["text"],
        interpretation=(
            f"Evaluating {len(enabled_measures)} quality measures with "
            f"{'equal' if len(set(weights.values())) <= 1 else 'custom'} weighting. "
            f"Data conflict resolution: {conflict_resolution.replace('_', ' ')}."
        ),
        parameters_extracted=params,
    )

    attributed_members = attribution_result.summary.get("attributed_population", [])

    measure_results = {}
    all_member_details = []
    data_quality_flags = []

    for measure_key in enabled_measures:
        if measure_key not in MEASURE_REGISTRY:
            data_quality_flags.append({
                "type": "unknown_measure",
                "measure": measure_key,
                "description": f"Measure '{measure_key}' not found in registry, skipping",
            })
            continue

        measure_cls = MEASURE_REGISTRY[measure_key]
        measure = measure_cls()
        result = measure.calculate(data, contract, attributed_members)

        measure_results[measure_key] = result.summary
        all_member_details.extend(result.member_details)

    # Calculate weighted composite score
    total_weight = 0.0
    weighted_sum = 0.0
    for measure_key, summary in measure_results.items():
        weight = weights.get(measure_key, 1.0 / len(enabled_measures))
        performance_rate = summary["performance_rate"]
        weighted_sum += performance_rate * weight
        total_weight += weight

    composite_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    src_lines = inspect.getsourcelines(calculate_quality_measures)
    start_line = src_lines[1]
    end_line = start_line + len(src_lines[0]) - 1

    elapsed_ms = int((time.time() - start) * 1000)

    return StepResult(
        step_name="quality",
        step_number=3,
        contract_clauses=[contract_clause],
        code_references=[CodeReference(
            module="step_3_quality",
            function="calculate_quality_measures",
            line_range=(start_line, end_line),
            logic_summary=(
                "Run each enabled quality measure (HEDIS methodology: "
                "denominator → exclusions → numerator → rate). "
                "Compute weighted composite score across all measures."
            ),
        )],
        summary={
            "composite_score": round(composite_score, 2),
            "measure_count": len(measure_results),
            "measures": measure_results,
        },
        member_details=all_member_details,
        data_quality_flags=data_quality_flags,
        execution_time_ms=elapsed_ms,
    )
