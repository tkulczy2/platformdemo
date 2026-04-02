import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getContract, updateContract, loadDemoContract } from '@/api/client';
import { classNames } from '@/utils/formatters';
import ClauseCard, { type ClauseData, type ClauseParameter } from './ClauseCard';

// ---------------------------------------------------------------------------
// Measure labels (human-readable)
// ---------------------------------------------------------------------------

const MEASURE_LABELS: Record<string, string> = {
  hba1c_poor_control: 'HbA1c Poor Control (<8%)',
  controlling_bp: 'Controlling Blood Pressure',
  breast_cancer_screening: 'Breast Cancer Screening',
  colorectal_screening: 'Colorectal Cancer Screening',
  depression_screening: 'Depression Screening',
};

// ---------------------------------------------------------------------------
// Section definitions -- maps clause_id prefix to display section
// ---------------------------------------------------------------------------

interface Section {
  key: string;
  title: string;
  description: string;
  clauseKeys: string[];
}

const SECTIONS: Section[] = [
  {
    key: 'eligibility',
    title: 'Eligibility',
    description: 'Defines which beneficiaries are eligible for attribution to the ACO.',
    clauseKeys: ['eligibility'],
  },
  {
    key: 'attribution',
    title: 'Attribution',
    description:
      'The two-step plurality method used to assign beneficiaries to ACO providers.',
    clauseKeys: ['attribution_step1', 'attribution_step2', 'attribution_tiebreaker'],
  },
  {
    key: 'quality',
    title: 'Quality Measures',
    description: 'HEDIS-based quality measures used to evaluate ACO performance.',
    clauseKeys: ['quality_measures'],
  },
  {
    key: 'cost',
    title: 'Cost Calculation',
    description: 'How total cost of care is calculated and expressed as PMPM.',
    clauseKeys: ['cost_calculation'],
  },
  {
    key: 'settlement',
    title: 'Settlement',
    description:
      'Benchmark comparison, savings calculation, and shared savings distribution.',
    clauseKeys: ['settlement'],
  },
  {
    key: 'quality_gate',
    title: 'Quality Gate',
    description: 'Minimum quality score required for shared savings eligibility.',
    clauseKeys: ['quality_gate'],
  },
];

// ---------------------------------------------------------------------------
// Build clause data from API response
// ---------------------------------------------------------------------------

function buildClauseData(
  clauseKey: string,
  clause: { clause_id: string; text: string; parameters: Record<string, unknown> },
  params: Record<string, unknown>,
): ClauseData {
  const titleMap: Record<string, string> = {
    eligibility: 'Beneficiary Eligibility',
    attribution_step1: 'Attribution Step 1 -- Primary Care Plurality',
    attribution_step2: 'Attribution Step 2 -- Expanded Provider Pool',
    attribution_tiebreaker: 'Attribution Tiebreaker',
    quality_measures: 'Quality Measure Specifications',
    cost_calculation: 'Total Cost of Care',
    settlement: 'Benchmark & Shared Savings',
    quality_gate: 'Quality Performance Gate',
  };

  const stepMap: Record<string, [number, string]> = {
    eligibility: [1, 'Eligibility'],
    attribution_step1: [2, 'Attribution'],
    attribution_step2: [2, 'Attribution'],
    attribution_tiebreaker: [2, 'Attribution'],
    quality_measures: [3, 'Quality'],
    cost_calculation: [4, 'Cost'],
    settlement: [5, 'Settlement'],
    quality_gate: [5, 'Settlement'],
  };

  const [linkedStep, linkedStepName] = stepMap[clauseKey] ?? [0, 'Unknown'];

  const parameters = buildParameters(clauseKey, clause.parameters, params);

  return {
    id: clause.clause_id,
    title: titleMap[clauseKey] ?? clauseKey,
    text: clause.text,
    linkedStep,
    linkedStepName,
    parameters,
  };
}

function buildParameters(
  clauseKey: string,
  _clauseParams: Record<string, unknown>,
  params: Record<string, unknown>,
): ClauseParameter[] {
  switch (clauseKey) {
    case 'eligibility':
      return [
        {
          key: 'minimum_enrollment_months',
          label: 'Minimum Enrollment Months',
          type: 'number',
          value: params.minimum_enrollment_months ?? 1,
          min: 1,
          max: 12,
          step: 1,
        },
        {
          key: 'exclude_esrd',
          label: 'Exclude ESRD Beneficiaries',
          type: 'toggle',
          value: params.exclude_esrd ?? true,
        },
      ];

    case 'attribution_step1':
      return [
        {
          key: 'attribution_method',
          label: 'Attribution Method',
          type: 'dropdown',
          value: params.attribution_method ?? 'plurality',
          options: [
            { label: 'Plurality of Primary Care Services', value: 'plurality' },
            { label: 'Voluntary Alignment', value: 'voluntary_alignment' },
            { label: 'Hybrid (Voluntary + Plurality)', value: 'hybrid' },
          ],
        },
        {
          key: 'provider_filter_step1',
          label: 'Step 1 Provider Filter',
          type: 'dropdown',
          value: params.provider_filter_step1 ?? 'pcp_only',
          options: [
            { label: 'PCPs Only', value: 'pcp_only' },
            { label: 'All ACO Participants', value: 'all_aco_participants' },
          ],
        },
      ];

    case 'attribution_tiebreaker':
      return [
        {
          key: 'tiebreaker',
          label: 'Tiebreaker Rule',
          type: 'dropdown',
          value: params.tiebreaker ?? 'most_recent_visit',
          options: [
            { label: 'Most Recent Visit', value: 'most_recent_visit' },
            { label: 'Alphabetical NPI', value: 'alphabetical_npi' },
            { label: 'Highest Cost Provider', value: 'highest_cost' },
          ],
        },
      ];

    case 'quality_measures':
      return [
        {
          key: 'measures',
          label: 'Active Quality Measures',
          type: 'checkbox-list',
          value: params.measures ?? [],
          items: Object.entries(MEASURE_LABELS).map(([value, label]) => ({
            value,
            label,
          })),
        },
        {
          key: 'conflict_resolution',
          label: 'Data Conflict Resolution',
          type: 'dropdown',
          value: params.conflict_resolution ?? 'most_recent_clinical',
          options: [
            { label: 'Most Recent Clinical Record', value: 'most_recent_clinical' },
            { label: 'Claims Data Only', value: 'claims_only' },
            { label: 'EHR Data Only', value: 'ehr_only' },
          ],
        },
      ];

    case 'cost_calculation':
      return [
        {
          key: 'cost_basis',
          label: 'Cost Basis',
          type: 'dropdown',
          value: params.cost_basis ?? 'allowed_amount',
          options: [
            { label: 'Allowed Amount', value: 'allowed_amount' },
            { label: 'Paid Amount', value: 'paid_amount' },
          ],
        },
        {
          key: 'include_pharmacy',
          label: 'Include Pharmacy Claims',
          type: 'toggle',
          value: params.include_pharmacy ?? false,
        },
        {
          key: 'runout_months',
          label: 'Claims Run-out Window (months)',
          type: 'number',
          value: params.runout_months ?? 3,
          min: 3,
          max: 12,
          step: 1,
        },
      ];

    case 'settlement':
      return [
        {
          key: 'benchmark_pmpm',
          label: 'Benchmark PMPM',
          type: 'currency',
          value: params.benchmark_pmpm ?? 1187.0,
          min: 0,
          step: 0.01,
        },
        {
          key: 'minimum_savings_rate',
          label: 'Minimum Savings Rate (MSR)',
          type: 'percentage',
          value: params.minimum_savings_rate ?? 0.02,
          min: 0.01,
          max: 0.05,
          step: 0.5,
        },
        {
          key: 'shared_savings_rate',
          label: 'Shared Savings Rate',
          type: 'percentage',
          value: params.shared_savings_rate ?? 0.5,
          min: 0.4,
          max: 0.75,
          step: 0.5,
        },
      ];

    case 'quality_gate':
      return [
        {
          key: 'quality_gate_threshold',
          label: 'Quality Gate Threshold',
          type: 'percentage',
          value: params.quality_gate_threshold ?? 0.4,
          min: 0.25,
          max: 0.7,
          step: 0.5,
        },
      ];

    default:
      return [];
  }
}

// ---------------------------------------------------------------------------
// ContractEditor component
// ---------------------------------------------------------------------------

export default function ContractEditor() {
  const navigate = useNavigate();

  // ---- State ----
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Raw API response
  const [clauses, setClauses] = useState<
    Record<string, { clause_id: string; text: string; parameters: Record<string, unknown> }>
  >({});
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [originalParams, setOriginalParams] = useState<Record<string, unknown>>({});

  // ---- Derived state ----
  const modifiedKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const key of Object.keys(params)) {
      if (JSON.stringify(params[key]) !== JSON.stringify(originalParams[key])) {
        keys.add(key);
      }
    }
    return keys;
  }, [params, originalParams]);

  const hasChanges = modifiedKeys.size > 0;

  // ---- Load contract ----
  const fetchContract = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getContract();
      if (!data.contract_loaded || !data.contract) {
        // No contract loaded yet -- leave state at defaults
        setClauses({});
        setParams({});
        setOriginalParams({});
        return;
      }
      const contract = data.contract;
      const clauseMap = contract.clauses ?? {};

      // Flatten all clause-level parameters into a single params object
      const flatParams: Record<string, unknown> = {};
      for (const clause of Object.values(clauseMap)) {
        if (clause.parameters) {
          Object.assign(flatParams, clause.parameters);
        }
      }

      setClauses(clauseMap);
      setParams(flatParams);
      setOriginalParams(flatParams);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load contract');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContract();
  }, [fetchContract]);

  // ---- Load demo contract ----
  const handleLoadDemo = useCallback(async () => {
    setLoadingDemo(true);
    setError(null);
    try {
      const data = await loadDemoContract();
      const contract = data.contract;
      if (!contract) {
        setError('Demo contract not found on server');
        return;
      }
      const clauseMap = contract.clauses ?? {};

      const flatParams: Record<string, unknown> = {};
      for (const clause of Object.values(clauseMap)) {
        if (clause.parameters) {
          Object.assign(flatParams, clause.parameters);
        }
      }

      setClauses(clauseMap);
      setParams(flatParams);
      setOriginalParams(flatParams);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load demo contract');
    } finally {
      setLoadingDemo(false);
    }
  }, []);

  // ---- Parameter change handler ----
  const handleParamChange = useCallback((key: string, value: unknown) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  }, []);

  // ---- Save / apply changes ----
  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await updateContract(params);
      setOriginalParams(params);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save contract');
    } finally {
      setSaving(false);
    }
  }, [params]);

  // ---- Reset changes ----
  const handleReset = useCallback(() => {
    setParams(originalParams);
  }, [originalParams]);

  // ---- Build clause card data ----
  const sectionClauseData = useMemo(() => {
    const result: Record<string, ClauseData[]> = {};
    for (const section of SECTIONS) {
      result[section.key] = section.clauseKeys
        .filter((ck) => clauses[ck])
        .map((ck) => buildClauseData(ck, clauses[ck], params));
    }
    return result;
  }, [clauses, params]);

  // ---- Render ----

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-brand-600" />
          <p className="text-sm text-gray-500">Loading contract configuration...</p>
        </div>
      </div>
    );
  }

  const isEmpty = Object.keys(clauses).length === 0;

  return (
    <div className="space-y-6">
      {/* ------------------------------------------------------------------ */}
      {/* Recalculate banner (sticky)                                        */}
      {/* ------------------------------------------------------------------ */}
      {hasChanges && (
        <div className="sticky top-[7.5rem] z-20 -mx-4 sm:-mx-6 lg:-mx-8">
          <div className="mx-4 sm:mx-6 lg:mx-8 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 shadow-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100">
                  <svg
                    className="h-5 w-5 text-amber-600"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-amber-800">
                    {modifiedKeys.size} parameter{modifiedKeys.size !== 1 ? 's' : ''} modified
                  </p>
                  <p className="text-xs text-amber-600">
                    Save changes and recalculate to see updated results.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleReset}
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-amber-700 hover:bg-amber-100 transition-colors"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="rounded-md bg-amber-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 disabled:opacity-60 transition-colors"
                >
                  {saving ? 'Saving...' : 'Save & Recalculate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Page header                                                        */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contract Configuration</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review the governing contract language and adjust configurable parameters. Every
            parameter change traces back to the specific contract clause that governs it.
          </p>
        </div>
        <button
          type="button"
          onClick={handleLoadDemo}
          disabled={loadingDemo}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60 transition-colors"
        >
          {loadingDemo ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Loading...
            </>
          ) : (
            <>
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              Load Sample Contract
            </>
          )}
        </button>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Error display                                                      */}
      {/* ------------------------------------------------------------------ */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 flex-shrink-0 text-red-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Empty state (no contract loaded)                                   */}
      {/* ------------------------------------------------------------------ */}
      {isEmpty && (
        <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white px-6 py-16 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-300"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
          <h3 className="mt-4 text-base font-semibold text-gray-900">No contract loaded</h3>
          <p className="mt-1 text-sm text-gray-500">
            Load the sample MSSP contract to see how contract language maps to calculation
            parameters.
          </p>
          <button
            type="button"
            onClick={handleLoadDemo}
            disabled={loadingDemo}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 transition-colors"
          >
            Load Sample Contract
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Two-column layout: sections on left, legend on right               */}
      {/* ------------------------------------------------------------------ */}
      {!isEmpty && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_300px]">
          {/* Left: clause sections */}
          <div className="space-y-8">
            {SECTIONS.map((section) => {
              const clauseCards = sectionClauseData[section.key] ?? [];
              if (clauseCards.length === 0) return null;
              return (
                <div key={section.key}>
                  <div className="mb-4">
                    <h2 className="text-lg font-bold text-gray-900">{section.title}</h2>
                    <p className="text-sm text-gray-500">{section.description}</p>
                  </div>
                  <div className="space-y-4">
                    {clauseCards.map((clause) => (
                      <ClauseCard
                        key={clause.id}
                        clause={clause}
                        modifiedKeys={modifiedKeys}
                        onChange={handleParamChange}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right: sidebar legend / summary */}
          <div className="hidden xl:block">
            <div className="sticky top-[9rem] space-y-6">
              {/* Contract info card */}
              <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-900">Contract Summary</h3>
                <dl className="mt-3 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Contract</dt>
                    <dd className="font-medium text-gray-900">MSSP ACO 2025</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Performance Year</dt>
                    <dd className="font-medium text-gray-900">2025</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Clauses</dt>
                    <dd className="font-medium text-gray-900">{Object.keys(clauses).length}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Parameters</dt>
                    <dd className="font-medium text-gray-900">{Object.keys(params).length}</dd>
                  </div>
                </dl>
              </div>

              {/* Step legend */}
              <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-900">Calculation Steps</h3>
                <p className="mt-1 text-xs text-gray-500">
                  Each clause governs a specific calculation step. Changing a parameter triggers
                  recalculation of the affected step and all downstream steps.
                </p>
                <ul className="mt-3 space-y-2">
                  {[
                    { step: 1, name: 'Eligibility', color: 'bg-blue-500' },
                    { step: 2, name: 'Attribution', color: 'bg-violet-500' },
                    { step: 3, name: 'Quality Measures', color: 'bg-emerald-500' },
                    { step: 4, name: 'Cost Calculation', color: 'bg-amber-500' },
                    { step: 5, name: 'Settlement', color: 'bg-rose-500' },
                    { step: 6, name: 'Reconciliation', color: 'bg-cyan-500' },
                  ].map((s) => (
                    <li key={s.step} className="flex items-center gap-2 text-xs text-gray-600">
                      <span className={classNames('h-2.5 w-2.5 rounded-full', s.color)} />
                      <span className="font-medium">Step {s.step}:</span>
                      {s.name}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Changes summary */}
              {hasChanges && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-amber-800">Pending Changes</h3>
                  <ul className="mt-2 space-y-1">
                    {Array.from(modifiedKeys).map((key) => (
                      <li key={key} className="text-xs text-amber-700">
                        <span className="font-mono">{key}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Bottom navigation                                                  */}
      {/* ------------------------------------------------------------------ */}
      {!isEmpty && (
        <div className="flex items-center justify-between border-t border-gray-200 pt-6">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          >
            &larr; Back to Data Upload
          </button>
          <button
            type="button"
            onClick={() => {
              if (hasChanges) {
                handleSave().then(() => navigate('/dashboard'));
              } else {
                navigate('/dashboard');
              }
            }}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60 transition-colors"
          >
            {saving ? 'Saving...' : 'Continue to Dashboard'}
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
