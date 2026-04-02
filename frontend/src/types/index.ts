// ---------------------------------------------------------------------------
// Data status
// ---------------------------------------------------------------------------

export interface FileQualityScore {
  file_name: string;
  rows: number;
  quality_score: number;
  completeness: number;
  issues: string[];
}

export interface DataStatus {
  files: Record<string, FileQualityScore>;
  overall_quality: number;
  ready: boolean;
}

// ---------------------------------------------------------------------------
// Contract
// ---------------------------------------------------------------------------

export interface ContractClause {
  id: string;
  title: string;
  text: string;
  section: string;
}

export interface ContractConfig {
  attribution_method: 'plurality' | 'voluntary_alignment' | 'hybrid';
  qualifying_cpt_codes: string[];
  tiebreaker: 'most_recent_visit' | 'alphabetical_npi' | 'highest_cost';
  provider_filter_step1: 'pcp_only' | 'all_aco_participants';
  minimum_enrollment_months: number;
  exclude_esrd: boolean;
  measures: string[];
  measure_weights: Record<string, number>;
  conflict_resolution: 'most_recent_clinical' | 'claims_only' | 'ehr_only';
  cost_basis: 'allowed_amount' | 'paid_amount';
  include_pharmacy: boolean;
  runout_months: number;
  benchmark_pmpm: number;
  minimum_savings_rate: number;
  shared_savings_rate: number;
  quality_gate_threshold: number;
}

// ---------------------------------------------------------------------------
// Provenance types (mirror engine/provenance.py)
// ---------------------------------------------------------------------------

export interface DataReference {
  file: string;
  row_index: number;
  columns: Record<string, string | number | boolean | null>;
  description: string;
}

export interface ContractClauseRef {
  clause_id: string;
  clause_text: string;
  section: string;
}

export interface CodeReference {
  module: string;
  function_name: string;
  start_line: number;
  end_line: number;
  file_path: string;
}

export interface MemberDetail {
  member_id: string;
  outcome: string;
  outcome_value: string | number | boolean | null;
  data_references: DataReference[];
  logic_trace: string[];
  flags: string[];
}

export interface StepResult {
  step_number: number;
  step_name: string;
  contract_clauses: ContractClauseRef[];
  code_references: CodeReference[];
  logic_summary: string;
  member_details: MemberDetail[];
  data_quality_flags: string[];
  execution_time_ms: number;
  aggregate_metrics: Record<string, number | string>;
}

export interface PipelineResult {
  steps: StepResult[];
  final_metrics: {
    attributed_population: number;
    quality_composite: number;
    actual_pmpm: number;
    benchmark_pmpm: number;
    total_savings: number;
    shared_savings: number;
    quality_gate_passed: boolean;
  };
  reconciliation: {
    discrepancies: Discrepancy[];
    total_financial_impact: number;
  };
  total_execution_time_ms: number;
  data_quality_summary: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

export interface MetricSummary {
  name: string;
  display_name: string;
  value: number | string;
  formatted_value: string;
  trend?: 'up' | 'down' | 'flat';
  drill_down_url: string;
  confidence_low?: number;
  confidence_high?: number;
}

export interface QualityMeasure {
  measure_id: string;
  measure_name: string;
  denominator: number;
  exclusions: number;
  eligible: number;
  numerator: number;
  rate: number;
  benchmark_rate: number;
  star_rating: number;
  weight: number;
}

// ---------------------------------------------------------------------------
// Reconciliation
// ---------------------------------------------------------------------------

export interface RelevantClause {
  clause_id: string;
  clause_text: string;
  interpretation: string;
}

export interface Discrepancy {
  id: string;
  category: 'attribution' | 'quality' | 'cost';
  subcategory: string;
  metric: string;
  metric_label: string;
  member_id: string;
  description: string;
  platform_value: string | number | null;
  payer_value: string | number | null;
  difference: number;
  financial_impact: number;
  root_cause: string;
  resolution_recommendation: string;
  relevant_clauses: RelevantClause[];
  data_sources: string[];
  data_references: DataReference[];
  detail?: {
    platform_numerator: number;
    payer_numerator: number;
    platform_denominator: number;
    payer_denominator: number;
  };
}

export interface ReconciliationSummary {
  total_discrepancies: number;
  financial_impact: number;
  categories: {
    category: string;
    count: number;
    impact: number;
    subcategories: { subcategory: string; count: number; impact: number }[];
  }[];
}

// ---------------------------------------------------------------------------
// Source code viewer
// ---------------------------------------------------------------------------

export interface SourceCode {
  module: string;
  function_name: string;
  source: string;
  start_line: number;
  end_line: number;
}
