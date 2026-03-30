"""Abstract base class for quality measures following HEDIS methodology.

Each measure follows: identify denominator → apply exclusions → evaluate numerator → calculate rate.
"""

import inspect
import time
from abc import ABC, abstractmethod

import pandas as pd

from engine.data_loader import LoadedData
from engine.provenance import (
    CodeReference,
    ContractClause,
    DataReference,
    MemberDetail,
    StepResult,
)


class BaseMeasure(ABC):
    """Abstract base class for quality measures."""

    measure_id: str
    measure_name: str
    measure_description: str
    data_sources_used: list[str]
    is_inverse: bool = False  # True if lower rate = better performance

    @abstractmethod
    def identify_denominator(
        self, data: LoadedData, attributed_members: list[str], members_df: pd.DataFrame,
    ) -> list[MemberDetail]:
        """Identify members eligible for this measure (denominator)."""

    @abstractmethod
    def apply_exclusions(
        self, denominator_members: list[MemberDetail], data: LoadedData,
    ) -> tuple[list[MemberDetail], list[MemberDetail]]:
        """Apply exclusions. Returns (eligible_after_exclusions, excluded_members)."""

    @abstractmethod
    def evaluate_numerator(
        self, eligible_members: list[MemberDetail], data: LoadedData,
    ) -> tuple[list[MemberDetail], list[MemberDetail]]:
        """Evaluate numerator. Returns (in_numerator, not_in_numerator)."""

    def get_contract_clause(self, contract: dict) -> ContractClause:
        """Build contract clause from contract config."""
        qual_clause = contract["clauses"]["quality_measures"]
        return ContractClause(
            clause_id=qual_clause["clause_id"],
            clause_text=qual_clause["text"],
            interpretation=(
                f"Measure: {self.measure_name} ({self.measure_id}). "
                f"{self.measure_description}"
            ),
            parameters_extracted={
                "measure_id": self.measure_id,
                "measure_name": self.measure_name,
                "is_inverse": self.is_inverse,
                "conflict_resolution": qual_clause["parameters"].get("conflict_resolution", "most_recent_clinical"),
            },
        )

    def calculate(
        self,
        data: LoadedData,
        contract: dict,
        attributed_members: list[str],
    ) -> StepResult:
        """Full calculation with provenance."""
        start = time.time()

        members_df = data.members[data.members["member_id"].isin(attributed_members)]
        contract_clause = self.get_contract_clause(contract)

        # Step 1: Denominator
        denominator = self.identify_denominator(data, attributed_members, members_df)
        denominator_ids = {m.member_id for m in denominator}

        # Step 2: Exclusions
        eligible, excluded = self.apply_exclusions(denominator, data)
        eligible_ids = {m.member_id for m in eligible}

        # Step 3: Numerator
        in_numerator, not_in_numerator = self.evaluate_numerator(eligible, data)

        # Combine all member details
        all_details = []
        for m in in_numerator:
            m.outcome = "in_numerator"
            all_details.append(m)
        for m in not_in_numerator:
            m.outcome = "not_in_numerator"
            all_details.append(m)
        for m in excluded:
            m.outcome = "excluded"
            all_details.append(m)

        # Members not in denominator at all
        denom_and_excluded_ids = denominator_ids | {m.member_id for m in excluded}
        for mid in attributed_members:
            if mid not in denom_and_excluded_ids:
                all_details.append(MemberDetail(
                    member_id=mid,
                    outcome="not_in_denominator",
                    reason=f"Does not meet denominator criteria for {self.measure_name}",
                ))

        # Calculate rate
        denominator_count = len(denominator)
        eligible_count = len(eligible)
        numerator_count = len(in_numerator)
        rate = (numerator_count / eligible_count * 100) if eligible_count > 0 else 0.0

        # Performance rate: for inverse measures, lower numerator rate = better
        if self.is_inverse:
            performance_rate = 100.0 - rate
        else:
            performance_rate = rate

        # Code reference
        calc_method = self.calculate
        src_lines = inspect.getsourcelines(type(self).evaluate_numerator)
        start_line = src_lines[1]
        end_line = start_line + len(src_lines[0]) - 1

        elapsed_ms = int((time.time() - start) * 1000)

        return StepResult(
            step_name=f"quality_{self.measure_id}",
            step_number=3,
            contract_clauses=[contract_clause],
            code_references=[CodeReference(
                module=f"measures.{type(self).__module__.split('.')[-1]}",
                function="evaluate_numerator",
                line_range=(start_line, end_line),
                logic_summary=self.measure_description,
            )],
            summary={
                "measure_id": self.measure_id,
                "measure_name": self.measure_name,
                "is_inverse": self.is_inverse,
                "denominator_count": denominator_count,
                "exclusion_count": len(excluded),
                "eligible_count": eligible_count,
                "numerator_count": numerator_count,
                "rate": round(rate, 2),
                "performance_rate": round(performance_rate, 2),
            },
            member_details=all_details,
            execution_time_ms=elapsed_ms,
        )
