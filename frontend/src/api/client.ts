/**
 * API client for the VBC Performance Intelligence backend.
 * All endpoints are relative -- Vite dev server proxies /api to localhost:8000.
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function uploadFile<T>(url: string, files: File | File[], fieldName = 'file'): Promise<T> {
  const form = new FormData();
  if (Array.isArray(files)) {
    files.forEach((f) => form.append(fieldName, f));
  } else {
    form.append(fieldName, files);
  }
  const res = await fetch(url, { method: 'POST', body: form });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upload ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Data endpoints
// ---------------------------------------------------------------------------

export async function loadDemoData() {
  return request<{ status: string }>('/api/data/load-demo', { method: 'POST' });
}

export async function uploadData(files: File[]) {
  return uploadFile<{ status: string }>('/api/data/upload', files, 'files');
}

export async function getDataStatus() {
  return request<DataStatusResponse>('/api/data/status');
}

// ---------------------------------------------------------------------------
// Contract endpoints
// ---------------------------------------------------------------------------

export async function getContract() {
  return request<ContractResponse>('/api/contract');
}

export async function updateContract(params: Record<string, unknown>) {
  return request<ContractResponse>('/api/contract', {
    method: 'PUT',
    body: JSON.stringify(params),
  });
}

export async function loadDemoContract() {
  return request<ContractResponse>('/api/contract/load-demo', { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Calculation endpoints
// ---------------------------------------------------------------------------

export async function runCalculation() {
  return request<CalculationResponse>('/api/calculate', { method: 'POST' });
}

export async function getResultsSummary() {
  return request<SummaryResponse>('/api/results/summary');
}

export async function getStepResult(stepNum: number) {
  return request<StepResultResponse>(`/api/results/step/${stepNum}`);
}

// ---------------------------------------------------------------------------
// Drill-down endpoints
// ---------------------------------------------------------------------------

export async function getMemberDrilldown(memberId: string) {
  return request<MemberDrilldownResponse>(`/api/drilldown/member/${memberId}`);
}

export async function getStepMemberDetail(stepNum: number, memberId: string) {
  return request<MemberDetailResponse>(`/api/drilldown/step/${stepNum}/member/${memberId}`);
}

export async function getStepMembers(stepNum: number, page = 1, pageSize = 50) {
  return request<StepMembersResponse>(
    `/api/drilldown/step/${stepNum}/members?page=${page}&page_size=${pageSize}`,
  );
}

export async function getMetricDrilldown(metricName: string) {
  return request<MetricDrilldownResponse>(`/api/drilldown/metric/${metricName}`);
}

// ---------------------------------------------------------------------------
// Reconciliation endpoints
// ---------------------------------------------------------------------------

export async function uploadPayerReport(file: File) {
  return uploadFile<{ status: string }>('/api/reconciliation/upload', file, 'file');
}

export async function loadDemoPayerReport() {
  return request<{ status: string }>('/api/reconciliation/load-demo', { method: 'POST' });
}

export async function getReconciliationSummary() {
  return request<ReconciliationSummaryResponse>('/api/reconciliation/summary');
}

export async function getReconciliationDetail(category: string) {
  return request<ReconciliationDetailResponse>(`/api/reconciliation/detail/${category}`);
}

// ---------------------------------------------------------------------------
// Code viewer endpoint
// ---------------------------------------------------------------------------

export async function getSourceCode(moduleName: string, functionName: string) {
  return request<SourceCodeResponse>(`/api/code/${moduleName}/${functionName}`);
}

// ---------------------------------------------------------------------------
// Response type aliases (light wrappers -- full types in types/index.ts)
// ---------------------------------------------------------------------------

interface DataStatusResponse {
  files: Record<string, { rows: number; quality_score: number; issues: string[] }>;
  overall_quality: number;
  ready: boolean;
}

interface ContractResponse {
  parameters: Record<string, unknown>;
  clauses: Array<{ id: string; title: string; text: string }>;
}

interface CalculationResponse {
  status: string;
  execution_time_ms: number;
  steps_completed: number;
}

interface SummaryResponse {
  metrics: Record<string, unknown>;
  steps: Array<{ step: number; name: string; status: string }>;
}

interface StepResultResponse {
  step: number;
  name: string;
  contract_clauses: Array<{ id: string; text: string }>;
  code_references: Array<{ module: string; function: string; lines: string }>;
  logic_summary: string;
  member_count: number;
  data_quality_flags: string[];
}

interface MemberDrilldownResponse {
  member_id: string;
  steps: Record<string, unknown>;
}

interface MemberDetailResponse {
  member_id: string;
  step: number;
  detail: Record<string, unknown>;
  data_references: Array<{ file: string; row: number; columns: Record<string, unknown> }>;
}

interface StepMembersResponse {
  step: number;
  page: number;
  page_size: number;
  total: number;
  members: Array<Record<string, unknown>>;
}

interface MetricDrilldownResponse {
  metric: string;
  value: unknown;
  contract_clauses: Array<{ id: string; text: string }>;
  code_references: Array<{ module: string; function: string; lines: string }>;
  logic_summary: string;
  member_details: Array<Record<string, unknown>>;
}

interface ReconciliationSummaryResponse {
  total_discrepancies: number;
  financial_impact: number;
  categories: Array<{ category: string; count: number; impact: number }>;
}

interface ReconciliationDetailResponse {
  category: string;
  discrepancies: Array<Record<string, unknown>>;
}

interface SourceCodeResponse {
  module: string;
  function: string;
  source: string;
  start_line: number;
  end_line: number;
}
