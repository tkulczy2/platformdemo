/**
 * API client for the VBC Performance Intelligence backend.
 * Dev: Vite proxies /api to localhost:8000.
 * Static demo (GitHub Pages): VITE_STATIC_SNAPSHOT=1 reads public/gh-pages-snapshot/*.json.
 */

import { fetchSnapshotJson, isStaticSnapshot } from '@/api/snapshot';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  if (isStaticSnapshot) {
    const method = options?.method ?? 'GET';
    if (method === 'GET') {
      return fetchSnapshotJson<T>(url);
    }
    if (method === 'DELETE') {
      return {} as T;
    }
    if (method === 'POST' || method === 'PUT') {
      return staticMutation<T>(url, options);
    }
  }

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

/** POST/PUT behavior when no backend — mirror demo state from snapshots. */
async function staticMutation<T>(url: string, options?: RequestInit): Promise<T> {
  if (url === '/api/data/load-demo') {
    return { status: 'success', message: 'Demo data (static snapshot)' } as T;
  }
  if (url === '/api/contract/load-demo') {
    const c = await fetchSnapshotJson<ContractGetResponse>('/api/contract');
    return {
      status: 'success',
      message: 'Sample MSSP contract (static snapshot)',
      contract: c.contract,
    } as T;
  }
  if (url === '/api/calculate') {
    const s = await fetchSnapshotJson<Record<string, unknown>>('/api/results/summary');
    const steps = (s.steps as unknown[]) ?? [];
    return {
      status: 'success',
      execution_time_ms: (s.total_execution_time_ms as number) ?? 0,
      steps_completed: steps.length,
    } as T;
  }
  if (url === '/api/reconciliation/load-demo') {
    return { status: 'success', message: 'Demo payer report (static snapshot)' } as T;
  }
  if (url === '/api/contract' && options?.method === 'PUT') {
    const c = await fetchSnapshotJson<ContractGetResponse>('/api/contract');
    return {
      status: 'success',
      message: 'Contract update ignored in static demo',
      contract: c.contract,
    } as T;
  }
  return { status: 'success' } as T;
}

async function uploadFile<T>(url: string, files: File | File[], fieldName = 'file'): Promise<T> {
  if (isStaticSnapshot) {
    return { status: 'success', message: 'Upload ignored in static demo' } as T;
  }
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

function staticExportBlocked(feature: string) {
  window.alert(
    `${feature} is not available in the static GitHub Pages demo — run the app locally with the API for full exports.`,
  );
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
  return request<ContractGetResponse>('/api/contract');
}

export async function updateContract(params: Record<string, unknown>) {
  return request<ContractMutationResponse>('/api/contract', {
    method: 'PUT',
    body: JSON.stringify(params),
  });
}

export async function loadDemoContract() {
  return request<ContractMutationResponse>('/api/contract/load-demo', { method: 'POST' });
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

export async function unloadPayerReport() {
  return request<{ status: string }>('/api/reconciliation/report', { method: 'DELETE' });
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
// Export endpoints
// ---------------------------------------------------------------------------

export function exportReconciliationPdf() {
  if (isStaticSnapshot) {
    staticExportBlocked('PDF export');
    return;
  }
  window.open('/api/export/reconciliation-pdf', '_blank');
}

export function exportCsv(tableName: string) {
  if (isStaticSnapshot) {
    staticExportBlocked('CSV export');
    return;
  }
  window.open(`/api/export/csv/${tableName}`, '_blank');
}

export function exportPipelineJson() {
  if (isStaticSnapshot) {
    staticExportBlocked('Pipeline JSON export');
    return;
  }
  window.open('/api/export/pipeline-json', '_blank');
}

// ---------------------------------------------------------------------------
// Clinical View endpoints
// ---------------------------------------------------------------------------

export async function getClinicalSchedule() {
  return request<WeeklyScheduleResponse>('/api/clinical/schedule');
}

export async function getClinicalDaySchedule(date: string) {
  return request<DayScheduleResponse>(`/api/clinical/schedule/${date}`);
}

export async function getClinicalBrief(appointmentId: string) {
  return request<PatientBriefApiResponse>(`/api/clinical/brief/${appointmentId}`);
}

export async function getClinicalBriefDrilldown(
  appointmentId: string,
  itemType: string,
  itemId: string,
) {
  return request<BriefDrilldownResponse>(
    `/api/clinical/brief/${appointmentId}/drilldown/${itemType}/${itemId}`,
  );
}

export async function getClinicalWeekSummary() {
  return request<WeekSummaryResponse>('/api/clinical/week-summary');
}

export async function submitClinicalFeedback(
  appointmentId: string,
  feedback: { item_type: string; item_id: string; feedback: string; note?: string },
) {
  return request<{ status: string }>(`/api/clinical/feedback/${appointmentId}`, {
    method: 'POST',
    body: JSON.stringify(feedback),
  });
}

// ---------------------------------------------------------------------------
// Response type aliases (light wrappers -- full types in types/index.ts)
// ---------------------------------------------------------------------------

interface DataStatusResponse {
  files: Record<string, { rows: number; quality_score: number; issues: string[] }>;
  overall_quality: number;
  ready: boolean;
}

interface ContractGetResponse {
  contract_loaded: boolean;
  contract: ContractData | null;
}

interface ContractMutationResponse {
  status?: string;
  message?: string;
  contract: ContractData | null;
}

interface ContractData {
  clauses: Record<string, { clause_id: string; text: string; parameters: Record<string, unknown> }>;
  [key: string]: unknown;
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
  step_number: number;
  name: string;
  step_name: string;
  contract_clauses: Array<{ id: string; text: string; section?: string; title?: string }>;
  code_references: Array<{ module: string; function: string; lines: string; start_line?: number; end_line?: number }>;
  logic_summary: string;
  member_count: number;
  member_details: Array<Record<string, unknown>>;
  data_quality_flags: string[];
}

interface MemberDrilldownResponse {
  member_id: string;
  steps: Record<string, unknown>;
}

interface MemberDetailResponse {
  member_id: string;
  step: number;
  step_number: number;
  step_name: string;
  detail: Record<string, unknown>;
  data_references: Array<{ file: string; row_index: number; row?: number; columns: Record<string, unknown>; description?: string }>;
  contract_clauses?: Array<{ id: string; text: string }>;
  code_references?: Array<{ module: string; function: string; lines: string }>;
}

interface StepMembersResponse {
  step: number;
  step_number: number;
  page: number;
  page_size: number;
  total: number;
  total_members: number;
  members: Array<Record<string, unknown>>;
}

interface MetricDrilldownResponse {
  metric: string;
  metric_name: string;
  value: unknown;
  metric_value: unknown;
  step_number: number;
  step_name: string;
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

interface WeeklyScheduleResponse {
  schedule_week: { start_date: string; end_date: string; practice_name: string; providers: Array<Record<string, unknown>> };
  days: Array<Record<string, unknown>>;
}

interface DayScheduleResponse {
  date: string;
  day_name: string;
  narrative_theme: string;
  appointments: Array<Record<string, unknown>>;
}

interface PatientBriefApiResponse extends Record<string, unknown> {
  appointment_id: string;
  member_id: string;
}

interface BriefDrilldownResponse {
  item_type: string;
  item_id: string;
  detail: Record<string, unknown>;
  provenance: Record<string, unknown>;
  clinical_question: string;
}

interface WeekSummaryResponse extends Record<string, unknown> {
  total_encounters: number;
}
