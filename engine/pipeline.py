"""Pipeline orchestrator — runs steps 1-6 in sequence with full provenance.

Each step receives loaded data, contract configuration, and results from
prior steps. Each step returns a StepResult with full provenance.
"""

import time

from engine.data_loader import LoadedData
from engine.provenance import PipelineResult, StepResult
from engine.step_1_eligibility import determine_eligibility
from engine.step_2_attribution import assign_attribution
from engine.step_3_quality import calculate_quality_measures
from engine.step_4_cost import calculate_cost
from engine.step_5_settlement import calculate_settlement
from engine.step_6_reconciliation import reconcile


class CalculationPipeline:
    """Orchestrates the six-step calculation pipeline.

    Each step receives:
    - The loaded data (DataFrames)
    - The contract configuration
    - Results from prior steps (for dependencies)

    Each step returns a StepResult with full provenance.
    """

    def run(
        self,
        data: LoadedData,
        contract: dict,
        payer_report: dict | None = None,
    ) -> PipelineResult:
        """Run the full pipeline and return a PipelineResult."""
        pipeline_start = time.time()
        steps: list[StepResult] = []

        # Step 1: Eligibility
        eligibility_result = determine_eligibility(data, contract)
        steps.append(eligibility_result)

        # Step 2: Attribution (depends on eligibility)
        attribution_result = assign_attribution(data, contract, eligibility_result)
        steps.append(attribution_result)

        # Step 3: Quality Measures (depends on attribution)
        quality_result = calculate_quality_measures(data, contract, attribution_result)
        steps.append(quality_result)

        # Step 4: Cost / PMPM (depends on attribution)
        cost_result = calculate_cost(data, contract, attribution_result)
        steps.append(cost_result)

        # Step 5: Settlement (depends on quality + cost)
        settlement_result = calculate_settlement(contract, quality_result, cost_result)
        steps.append(settlement_result)

        # Step 6: Reconciliation (optional, if payer report provided)
        reconciliation = None
        if payer_report:
            reconciliation = reconcile(steps, payer_report, data)

        total_ms = int((time.time() - pipeline_start) * 1000)

        return PipelineResult(
            steps=steps,
            final_metrics=self._aggregate_metrics(steps),
            reconciliation=reconciliation,
            total_execution_time_ms=total_ms,
        )

    def _aggregate_metrics(self, steps: list[StepResult]) -> dict:
        """Aggregate top-level metrics from all steps."""
        metrics = {}
        for step in steps:
            if step.step_name == "eligibility":
                metrics["total_members"] = step.summary.get("total_members", 0)
                metrics["eligible_count"] = step.summary.get("eligible_count", 0)
            elif step.step_name == "attribution":
                metrics["attributed_population"] = step.summary.get("attributed_count", 0)
                metrics["attributed_step1"] = step.summary.get("attributed_step1", 0)
                metrics["attributed_step2"] = step.summary.get("attributed_step2", 0)
            elif step.step_name == "quality":
                metrics["quality_composite"] = step.summary.get("composite_score", 0)
                metrics["quality_measures"] = step.summary.get("measures", {})
            elif step.step_name == "cost":
                metrics["actual_pmpm"] = step.summary.get("actual_pmpm", 0)
                metrics["raw_pmpm"] = step.summary.get("raw_pmpm", 0)
                metrics["total_member_months"] = step.summary.get("total_member_months", 0)
            elif step.step_name == "settlement":
                metrics["benchmark_pmpm"] = step.summary.get("benchmark_pmpm", 0)
                metrics["gross_savings"] = step.summary.get("gross_savings", 0)
                metrics["shared_savings_amount"] = step.summary.get("shared_savings_amount", 0)
                metrics["settlement_status"] = step.summary.get("settlement_status", "unknown")
                metrics["msr_passed"] = step.summary.get("msr_passed", False)
                metrics["quality_gate_passed"] = step.summary.get("quality_gate_passed", False)
        return metrics
