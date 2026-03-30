"""Provenance tracking dataclasses — the core data model for transparent calculations.

Every calculation step produces a StepResult containing full provenance:
contract clauses, code references, member-level details, and data quality flags.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DataReference:
    """Points to specific rows in a specific source file."""
    source_file: str
    row_indices: list[int]
    columns_used: list[str]
    description: str


@dataclass
class ContractClause:
    """The contract language governing a calculation step."""
    clause_id: str
    clause_text: str
    interpretation: str
    parameters_extracted: dict[str, Any]


@dataclass
class CodeReference:
    """Points to the code that executed this logic."""
    module: str
    function: str
    line_range: tuple[int, int]
    logic_summary: str


@dataclass
class MemberDetail:
    """Per-member detail for drill-down."""
    member_id: str
    outcome: str
    reason: str
    data_references: list[DataReference] = field(default_factory=list)
    intermediate_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Complete output of one pipeline step."""
    step_name: str
    step_number: int
    contract_clauses: list[ContractClause]
    code_references: list[CodeReference]
    summary: dict[str, Any]
    member_details: list[MemberDetail]
    data_quality_flags: list[dict[str, Any]] = field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PipelineResult:
    """Complete output of the full pipeline."""
    steps: list[StepResult]
    final_metrics: dict[str, Any]
    reconciliation: dict[str, Any] | None = None
    total_execution_time_ms: int = 0
