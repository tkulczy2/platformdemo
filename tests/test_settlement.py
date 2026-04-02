"""Tests for Step 5: Settlement Calculation — benchmark, gates, shared savings."""

import pytest

from engine.provenance import StepResult
from engine.step_5_settlement import calculate_settlement


def _make_quality_result(composite_score):
    """Create a minimal StepResult for quality with a given composite score."""
    return StepResult(
        step_name="quality",
        step_number=3,
        contract_clauses=[],
        code_references=[],
        summary={"composite_score": composite_score},
        member_details=[],
    )


def _make_cost_result(actual_pmpm, total_member_months, pmpm_low=None, pmpm_high=None):
    """Create a minimal StepResult for cost with given values."""
    return StepResult(
        step_name="cost",
        step_number=4,
        contract_clauses=[],
        code_references=[],
        summary={
            "actual_pmpm": actual_pmpm,
            "total_member_months": total_member_months,
            "pmpm_confidence_low": pmpm_low or actual_pmpm,
            "pmpm_confidence_high": pmpm_high or actual_pmpm,
        },
        member_details=[],
    )


def _make_contract(benchmark=1187.0, msr=0.02, shared_rate=0.50, quality_gate=0.40):
    """Create a contract dict with settlement parameters."""
    return {
        "clauses": {
            "settlement": {
                "clause_id": "SETTLE-1.0",
                "text": "Test settlement clause.",
                "parameters": {
                    "benchmark_pmpm": benchmark,
                    "minimum_savings_rate": msr,
                    "shared_savings_rate": shared_rate,
                },
            },
            "quality_gate": {
                "clause_id": "SETTLE-1.1",
                "text": "Test quality gate clause.",
                "parameters": {
                    "quality_gate_threshold": quality_gate,
                },
            },
        }
    }


class TestSettlementBasics:
    def test_returns_step_result(self):
        contract = _make_contract()
        quality = _make_quality_result(80.0)
        cost = _make_cost_result(1100.0, 10000)
        result = calculate_settlement(contract, quality, cost)
        assert isinstance(result, StepResult)

    def test_step_metadata(self):
        contract = _make_contract()
        quality = _make_quality_result(80.0)
        cost = _make_cost_result(1100.0, 10000)
        result = calculate_settlement(contract, quality, cost)
        assert result.step_name == "settlement"
        assert result.step_number == 5


class TestSettlementMath:
    def test_gross_savings_calculation(self):
        """Gross savings = (benchmark - actual) * member_months."""
        contract = _make_contract(benchmark=1200.0)
        cost = _make_cost_result(actual_pmpm=1100.0, total_member_months=10000)
        quality = _make_quality_result(80.0)
        result = calculate_settlement(contract, quality, cost)

        expected_gross = (1200.0 - 1100.0) * 10000  # $1,000,000
        assert abs(result.summary["gross_savings"] - expected_gross) < 1.0

    def test_shared_savings_when_gates_pass(self):
        """When both gates pass: shared savings = gross * shared_rate."""
        contract = _make_contract(benchmark=1200.0, msr=0.02, shared_rate=0.50, quality_gate=0.40)
        cost = _make_cost_result(actual_pmpm=1100.0, total_member_months=10000)
        quality = _make_quality_result(80.0)  # > 40% gate
        result = calculate_settlement(contract, quality, cost)

        savings_rate = (1200.0 - 1100.0) / 1200.0  # ~8.3% > 2% MSR
        assert result.summary["msr_passed"] is True
        assert result.summary["quality_gate_passed"] is True
        expected_shared = (1200.0 - 1100.0) * 10000 * 0.50
        assert abs(result.summary["shared_savings_amount"] - expected_shared) < 1.0

    def test_zero_savings_when_msr_fails(self):
        """If savings rate below MSR, shared savings = $0."""
        contract = _make_contract(benchmark=1200.0, msr=0.02)
        # Actual is only 0.5% below benchmark — fails 2% MSR
        cost = _make_cost_result(actual_pmpm=1194.0, total_member_months=10000)
        quality = _make_quality_result(80.0)
        result = calculate_settlement(contract, quality, cost)

        assert result.summary["msr_passed"] is False
        assert result.summary["shared_savings_amount"] == 0.0

    def test_zero_savings_when_quality_gate_fails(self):
        """If quality composite below gate threshold, shared savings = $0."""
        contract = _make_contract(benchmark=1200.0, quality_gate=0.40)
        cost = _make_cost_result(actual_pmpm=1100.0, total_member_months=10000)
        quality = _make_quality_result(30.0)  # 30% < 40% gate
        result = calculate_settlement(contract, quality, cost)

        assert result.summary["quality_gate_passed"] is False
        assert result.summary["shared_savings_amount"] == 0.0

    def test_zero_savings_when_both_gates_fail(self):
        contract = _make_contract(benchmark=1200.0, msr=0.02, quality_gate=0.40)
        cost = _make_cost_result(actual_pmpm=1195.0, total_member_months=10000)
        quality = _make_quality_result(30.0)
        result = calculate_settlement(contract, quality, cost)

        assert result.summary["msr_passed"] is False
        assert result.summary["quality_gate_passed"] is False
        assert result.summary["shared_savings_amount"] == 0.0

    def test_no_savings_when_costs_exceed_benchmark(self):
        """When actual > benchmark, gross savings is negative."""
        contract = _make_contract(benchmark=1000.0)
        cost = _make_cost_result(actual_pmpm=1100.0, total_member_months=10000)
        quality = _make_quality_result(80.0)
        result = calculate_settlement(contract, quality, cost)

        assert result.summary["gross_savings"] < 0
        # No shared savings when there are losses
        assert result.summary["shared_savings_amount"] <= 0


class TestSettlementWithDemoData:
    def test_settlement_with_real_pipeline(self, pipeline_result):
        """The full pipeline produces a valid settlement step."""
        settlement = pipeline_result.steps[4]  # Step 5 is index 4
        assert settlement.step_name == "settlement"
        assert "benchmark_pmpm" in settlement.summary
        assert "actual_pmpm" in settlement.summary
        assert "shared_savings_amount" in settlement.summary
        assert "settlement_status" in settlement.summary

    def test_settlement_status_valid(self, pipeline_result):
        settlement = pipeline_result.steps[4]
        assert settlement.summary["settlement_status"] in ("eligible", "ineligible")


class TestSettlementProvenance:
    def test_has_two_contract_clauses(self):
        """Settlement should reference both the benchmark and quality gate clauses."""
        contract = _make_contract()
        quality = _make_quality_result(80.0)
        cost = _make_cost_result(1100.0, 10000)
        result = calculate_settlement(contract, quality, cost)
        assert len(result.contract_clauses) == 2

    def test_member_details_present(self):
        contract = _make_contract()
        quality = _make_quality_result(80.0)
        cost = _make_cost_result(1100.0, 10000)
        result = calculate_settlement(contract, quality, cost)
        assert len(result.member_details) >= 1

    def test_confidence_range_in_summary(self):
        contract = _make_contract()
        quality = _make_quality_result(80.0)
        cost = _make_cost_result(1100.0, 10000, pmpm_low=1050.0, pmpm_high=1150.0)
        result = calculate_settlement(contract, quality, cost)
        assert "confidence_range" in result.summary or "shared_savings_low" in result.summary.get("confidence_range", result.summary)
