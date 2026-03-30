import { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  getStepResult,
  getStepMemberDetail,
  getStepMembers,
  getMetricDrilldown,
} from '@/api/client';
import { classNames } from '@/utils/formatters';
import ContractPanel from './ContractPanel';
import LogicPanel from './LogicPanel';
import CodePanel from './CodePanel';

// Step name mapping
const STEP_NAMES: Record<number, string> = {
  1: 'Eligibility & Enrollment',
  2: 'Attribution',
  3: 'Quality Measures',
  4: 'Cost & Utilization',
  5: 'Settlement',
  6: 'Reconciliation',
};

interface StepData {
  step: number;
  name: string;
  contract_clauses: Array<{ id: string; text: string; section?: string; title?: string }>;
  code_references: Array<{ module: string; function: string; lines: string }>;
  logic_summary: string;
  member_count: number;
  data_quality_flags: string[];
}

interface MemberData {
  member_id: string;
  step: number;
  detail: {
    outcome?: string;
    outcome_value?: string | number | boolean | null;
    logic_trace?: string[];
    flags?: string[];
    intermediate_values?: Array<{ label: string; value: string | number | boolean | null }>;
    [key: string]: unknown;
  };
  data_references: Array<{
    file: string;
    row_index: number; // kept as-is even though API uses row
    columns: Record<string, string | number | boolean | null>;
    description?: string;
  }>;
}

interface MemberListItem {
  member_id: string;
  outcome?: string;
  [key: string]: unknown;
}

interface MetricData {
  metric: string;
  value: unknown;
  contract_clauses: Array<{ id: string; text: string; section?: string; title?: string }>;
  code_references: Array<{ module: string; function: string; lines: string }>;
  logic_summary: string;
  member_details: Array<Record<string, unknown>>;
}

/**
 * Screen 4: Three-panel drill-down provenance view.
 *
 * This is the signature UX of the platform. For any metric or member,
 * the user sees three panels side by side:
 *   Left:   Contract language governing the calculation
 *   Center: Plain-English interpretation + source data rows
 *   Right:  The actual Python code that executed the logic
 *
 * Routes:
 *   /drilldown/:stepNum/:memberId  -- direct member drill-down
 *   /drilldown/metric/:metricName  -- metric-level, then drill into members
 */
export default function DrilldownView() {
  const { stepNum, memberId, metricName } = useParams<{
    stepNum?: string;
    memberId?: string;
    metricName?: string;
  }>();
  const navigate = useNavigate();

  // Data state
  const [stepData, setStepData] = useState<StepData | null>(null);
  const [memberData, setMemberData] = useState<MemberData | null>(null);
  const [metricData, setMetricData] = useState<MetricData | null>(null);
  const [memberList, setMemberList] = useState<MemberListItem[]>([]);
  const [memberListPage, setMemberListPage] = useState(1);
  const [memberListTotal, setMemberListTotal] = useState(0);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(memberId ?? null);

  const parsedStep = stepNum ? parseInt(stepNum, 10) : null;
  const currentStepName = parsedStep ? STEP_NAMES[parsedStep] || `Step ${parsedStep}` : '';

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  // Load step-level data
  const loadStepData = useCallback(async (step: number) => {
    try {
      const data = await getStepResult(step);
      setStepData(data);
    } catch (err) {
      console.error('Failed to load step data:', err);
    }
  }, []);

  // Load member list for the step
  const loadMemberList = useCallback(async (step: number, page: number) => {
    try {
      const data = await getStepMembers(step, page, 50);
      setMemberList(data.members as MemberListItem[]);
      setMemberListPage(data.page);
      setMemberListTotal(data.total);
    } catch (err) {
      console.error('Failed to load member list:', err);
    }
  }, []);

  // Load single member detail
  const loadMemberDetail = useCallback(async (step: number, mId: string) => {
    try {
      const data = await getStepMemberDetail(step, mId);
      // Normalize API response: backend uses 'row' but our type uses 'row_index'
      const normalized: MemberData = {
        member_id: data.member_id,
        step: data.step,
        detail: data.detail as MemberData['detail'],
        data_references: (data.data_references || []).map((ref) => ({
          file: ref.file,
          row_index: (ref as Record<string, unknown>).row_index as number ?? ref.row,
          columns: ref.columns as Record<string, string | number | boolean | null>,
          description: (ref as Record<string, unknown>).description as string | undefined,
        })),
      };
      setMemberData(normalized);
    } catch (err) {
      console.error('Failed to load member detail:', err);
      setMemberData(null);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    let cancelled = false;

    async function init() {
      setLoading(true);
      setError(null);

      try {
        if (metricName) {
          // Metric-level drill-down
          const mData = await getMetricDrilldown(metricName);
          if (!cancelled) {
            setMetricData(mData as unknown as MetricData);
            // Also build a member list from the metric's member_details
            const members = (mData.member_details || []).map((m) => ({
              member_id: (m.member_id as string) || '',
              outcome: (m.outcome as string) || '',
              ...m,
            }));
            setMemberList(members);
            setMemberListTotal(members.length);
          }
        } else if (parsedStep) {
          // Step + optional member drill-down
          await loadStepData(parsedStep);
          await loadMemberList(parsedStep, 1);

          if (memberId && !cancelled) {
            setSelectedMemberId(memberId);
            await loadMemberDetail(parsedStep, memberId);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load drill-down data');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [parsedStep, memberId, metricName, loadStepData, loadMemberList, loadMemberDetail]);

  // When a member is selected from the list
  async function handleSelectMember(mId: string) {
    setSelectedMemberId(mId);
    if (parsedStep) {
      await loadMemberDetail(parsedStep, mId);
      // Update the URL without full reload
      navigate(`/drilldown/${parsedStep}/${mId}`, { replace: true });
    }
  }

  // Navigate to next/previous member
  function handleNavigateMember(direction: 'prev' | 'next') {
    const currentIndex = memberList.findIndex((m) => m.member_id === selectedMemberId);
    if (currentIndex === -1) return;

    const newIndex = direction === 'prev' ? currentIndex - 1 : currentIndex + 1;
    if (newIndex >= 0 && newIndex < memberList.length) {
      handleSelectMember(memberList[newIndex].member_id);
    }
  }

  // Pagination for member list
  async function handlePageChange(page: number) {
    if (parsedStep) {
      await loadMemberList(parsedStep, page);
    }
  }

  // Determine current member index for prev/next navigation
  const currentMemberIndex = memberList.findIndex((m) => m.member_id === selectedMemberId);
  const hasPrev = currentMemberIndex > 0;
  const hasNext = currentMemberIndex >= 0 && currentMemberIndex < memberList.length - 1;

  // Derive panel data from step or metric context
  const contractClauses = metricData?.contract_clauses ?? stepData?.contract_clauses ?? [];
  const codeReferences = metricData?.code_references ?? stepData?.code_references ?? [];
  const logicSummary = metricData?.logic_summary ?? stepData?.logic_summary ?? '';

  // Build member detail for LogicPanel
  const logicMemberDetail = memberData
    ? {
        member_id: memberData.member_id,
        outcome: memberData.detail?.outcome ?? '',
        outcome_value: memberData.detail?.outcome_value ?? null,
        data_references: memberData.data_references.map((ref) => ({
          file: ref.file,
          row_index: ref.row_index,
          columns: ref.columns,
          description: ref.description,
        })),
        logic_trace: memberData.detail?.logic_trace ?? [],
        flags: memberData.detail?.flags ?? [],
      }
    : null;

  const intermediateValues = memberData?.detail?.intermediate_values ?? [];

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3 text-gray-500">
          <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm font-medium">Loading provenance data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-4 max-w-md text-center">
          <p className="text-sm text-red-700 mb-3">{error}</p>
          <Link
            to="/dashboard"
            className="text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(memberListTotal / 50);

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)]">
      {/* ================================================================== */}
      {/* Top bar: breadcrumb, member nav, back button                        */}
      {/* ================================================================== */}
      <div className="flex-shrink-0 flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2.5 rounded-t-xl">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm">
          <Link
            to="/dashboard"
            className="text-gray-500 hover:text-brand-600 transition-colors"
          >
            Dashboard
          </Link>
          <svg className="h-3.5 w-3.5 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
          </svg>

          {metricName ? (
            <span className="font-medium text-gray-900">{metricName}</span>
          ) : (
            <>
              <span className="text-gray-700 font-medium">{currentStepName}</span>
              {selectedMemberId && (
                <>
                  <svg className="h-3.5 w-3.5 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                  </svg>
                  <span className="font-mono text-gray-900">{selectedMemberId}</span>
                </>
              )}
            </>
          )}
        </nav>

        {/* Controls */}
        <div className="flex items-center gap-3">
          {/* Member navigation arrows */}
          {selectedMemberId && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleNavigateMember('prev')}
                disabled={!hasPrev}
                className={classNames(
                  'rounded-md p-1.5 transition-colors',
                  hasPrev
                    ? 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    : 'text-gray-300 cursor-not-allowed',
                )}
                title="Previous member"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
              <span className="text-xs text-gray-400 min-w-[4rem] text-center">
                {currentMemberIndex >= 0
                  ? `${currentMemberIndex + 1} of ${memberList.length}`
                  : ''}
              </span>
              <button
                onClick={() => handleNavigateMember('next')}
                disabled={!hasNext}
                className={classNames(
                  'rounded-md p-1.5 transition-colors',
                  hasNext
                    ? 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    : 'text-gray-300 cursor-not-allowed',
                )}
                title="Next member"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          )}

          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </div>

      {/* ================================================================== */}
      {/* Main content: member sidebar + three panels                         */}
      {/* ================================================================== */}
      <div className="flex-1 flex overflow-hidden">
        {/* -------------------------------------------------------------- */}
        {/* Member list sidebar                                             */}
        {/* -------------------------------------------------------------- */}
        <div className="flex-shrink-0 w-52 border-r border-gray-200 bg-white flex flex-col">
          <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
            <p className="text-xs font-semibold text-gray-600">
              Members
              <span className="ml-1 font-normal text-gray-400">({memberListTotal})</span>
            </p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {memberList.map((m) => (
              <button
                key={m.member_id}
                onClick={() => handleSelectMember(m.member_id)}
                className={classNames(
                  'w-full text-left px-3 py-2 border-b border-gray-50 transition-colors text-xs',
                  m.member_id === selectedMemberId
                    ? 'bg-brand-50 text-brand-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-50',
                )}
              >
                <span className="font-mono block">{m.member_id}</span>
                {m.outcome && (
                  <span className={classNames(
                    'text-[10px] block mt-0.5',
                    m.member_id === selectedMemberId ? 'text-brand-600' : 'text-gray-400',
                  )}>
                    {String(m.outcome).slice(0, 30)}
                  </span>
                )}
              </button>
            ))}
          </div>
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex-shrink-0 border-t border-gray-200 px-3 py-2 flex items-center justify-between">
              <button
                onClick={() => handlePageChange(memberListPage - 1)}
                disabled={memberListPage <= 1}
                className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed"
              >
                Prev
              </button>
              <span className="text-[10px] text-gray-400">
                {memberListPage}/{totalPages}
              </span>
              <button
                onClick={() => handlePageChange(memberListPage + 1)}
                disabled={memberListPage >= totalPages}
                className="text-xs text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* -------------------------------------------------------------- */}
        {/* Three-panel provenance view                                     */}
        {/* -------------------------------------------------------------- */}
        <div className="flex-1 grid grid-cols-[30fr_40fr_30fr] divide-x divide-gray-200 overflow-hidden">
          {/* Left: Contract language */}
          <div className="overflow-hidden flex flex-col bg-white">
            <ContractPanel
              clauses={contractClauses}
            />
          </div>

          {/* Center: Logic + Data */}
          <div className="overflow-hidden flex flex-col bg-white">
            <LogicPanel
              logicSummary={logicSummary}
              memberDetail={logicMemberDetail}
              intermediateValues={intermediateValues}
              stepName={currentStepName || metricName}
            />
          </div>

          {/* Right: Source code */}
          <div className="overflow-hidden flex flex-col bg-white">
            <CodePanel codeReferences={codeReferences} />
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* Data quality flags footer                                           */}
      {/* ================================================================== */}
      {stepData && stepData.data_quality_flags.length > 0 && (
        <div className="flex-shrink-0 border-t border-amber-200 bg-amber-50 px-4 py-2 flex items-center gap-3">
          <svg className="h-4 w-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <div className="flex flex-wrap gap-2">
            {stepData.data_quality_flags.map((flag, i) => (
              <span key={i} className="text-xs text-amber-700">{flag}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
