import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  runCalculation,
  getResultsSummary,
  getReconciliationSummary,
  exportPipelineJson,
} from '@/api/client';
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters';
import type { QualityMeasure } from '@/types';
import MetricCard from './MetricCard';
import type { MetricStatus } from './MetricCard';
import QualityScorecard from './QualityScorecard';
import CostChart from './CostChart';

// ---------------------------------------------------------------------------
// Types for API responses (kept local since they map to the summary shape)
// ---------------------------------------------------------------------------

interface Metrics {
  attributed_population: number;
  quality_composite: number;
  actual_pmpm: number;
  benchmark_pmpm: number;
  total_savings: number;
  gross_savings: number;
  shared_savings_amount: number;
  quality_gate_passed: boolean;
  msr_passed: boolean;
  member_months: number;
  confidence_low_pmpm?: number;
  confidence_high_pmpm?: number;
  [key: string]: unknown;
}

interface ReconciliationInfo {
  total_discrepancies: number;
  financial_impact: number;
}

type Phase = 'idle' | 'calculating' | 'loading' | 'ready' | 'error';

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ResultsDashboard() {
  const navigate = useNavigate();

  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [qualityMeasures, setQualityMeasures] = useState<QualityMeasure[]>([]);
  const [recon, setRecon] = useState<ReconciliationInfo | null>(null);

  // -----------------------------------------------------------------------
  // Fetch existing results (no pipeline run)
  // -----------------------------------------------------------------------

  const fetchResults = useCallback(async () => {
    setPhase('loading');
    const summary = await getResultsSummary() as unknown as Record<string, unknown>;
    const finalMetrics = (summary.final_metrics ?? summary.metrics ?? summary) as unknown as Metrics;
    setMetrics(finalMetrics);
    setExecutionTime((summary.total_execution_time_ms as number) ?? null);

    // Extract quality measures from the metrics for the scorecard
    try {
      const qm = finalMetrics.quality_measures as Record<string, Record<string, unknown>> | undefined;
      if (qm) {
        const mapped: QualityMeasure[] = Object.entries(qm).map(([key, m]) => ({
          measure_id: key,
          measure_name: (m.measure_name ?? key) as string,
          denominator: (m.denominator_count ?? m.denominator ?? 0) as number,
          exclusions: (m.exclusion_count ?? m.exclusions ?? 0) as number,
          eligible: (m.eligible_count ?? m.eligible ?? 0) as number,
          numerator: (m.numerator_count ?? m.numerator ?? 0) as number,
          rate: (m.rate ?? 0) as number,
          benchmark_rate: (m.benchmark_rate ?? 0) as number,
          star_rating: (m.star_rating ?? 0) as number,
          weight: (m.weight ?? 0.2) as number,
        }));
        setQualityMeasures(mapped);
      }
    } catch {
      // Quality measures not available -- non-fatal
    }

    // Fetch reconciliation summary (may not exist)
    try {
      const reconData = await getReconciliationSummary() as unknown as Record<string, unknown>;
      setRecon({
        total_discrepancies: (reconData.discrepancy_count ?? reconData.total_discrepancies ?? 0) as number,
        financial_impact: (reconData.total_financial_impact ?? reconData.financial_impact ?? 0) as number,
      });
    } catch {
      // No reconciliation data available
    }

    setPhase('ready');
  }, []);

  // -----------------------------------------------------------------------
  // Run pipeline + fetch results
  // -----------------------------------------------------------------------

  const calculate = useCallback(async () => {
    try {
      setPhase('calculating');
      setError(null);

      const calcResult = await runCalculation() as unknown as Record<string, unknown>;
      setExecutionTime((calcResult.total_execution_time_ms ?? calcResult.execution_time_ms ?? 0) as number);

      await fetchResults();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
      setPhase('error');
    }
  }, [fetchResults]);

  // On mount: try to load existing results first, only run pipeline if none exist
  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await fetchResults();
      } catch {
        // No existing results -- run the pipeline
        if (!cancelled) await calculate();
      }
    }
    init();
    return () => { cancelled = true; };
  }, [fetchResults, calculate]);

  // -----------------------------------------------------------------------
  // Navigation helpers
  // -----------------------------------------------------------------------

  const drillMetric = (name: string) => navigate(`/drilldown/metric/${name}`);
  const drillStep = (step: number) => navigate(`/drilldown/metric/step_${step}`);
  const goRecon = () => navigate('/reconciliation');

  // -----------------------------------------------------------------------
  // Determine metric statuses
  // -----------------------------------------------------------------------

  function savingsStatus(): MetricStatus {
    if (!metrics) return 'neutral';
    return metrics.gross_savings > 0 ? 'green' : 'red';
  }

  function qualityStatus(): MetricStatus {
    if (!metrics) return 'neutral';
    const q = metrics.quality_composite;
    // quality_composite comes as a percentage (e.g. 47.24), not a decimal
    if (q >= 75) return 'green';
    if (q >= 50) return 'yellow';
    return 'red';
  }

  function settlementStatus(): MetricStatus {
    if (!metrics) return 'neutral';
    if (metrics.quality_gate_passed && metrics.msr_passed) return 'green';
    if (metrics.quality_gate_passed || metrics.msr_passed) return 'yellow';
    return 'red';
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  // -- Calculating / loading state ----------------------------------------
  if (phase === 'calculating' || phase === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center gap-6 py-24">
        <div className="relative h-16 w-16">
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-900">
            {phase === 'calculating' ? 'Running calculation pipeline...' : 'Loading results...'}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            {phase === 'calculating'
              ? 'Executing steps 1-6 with full provenance tracking'
              : 'Fetching metrics, quality measures, and reconciliation data'}
          </p>
        </div>
      </div>
    );
  }

  // -- Error state --------------------------------------------------------
  if (phase === 'error') {
    const isMissingData = error?.toLowerCase().includes('data');
    const isMissingContract = error?.toLowerCase().includes('contract');

    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6">
          <div className="flex items-start gap-3">
            <svg className="mt-0.5 h-5 w-5 text-red-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="font-semibold text-red-800">Calculation Failed</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              {(isMissingData || isMissingContract) && (
                <div className="mt-3 space-y-2">
                  <p className="text-xs font-medium text-red-800">Before calculating, you need to:</p>
                  <ul className="list-inside list-disc text-xs text-red-700 space-y-1">
                    {isMissingData && (
                      <li>
                        <button onClick={() => navigate('/')} className="underline hover:text-red-900">
                          Load or upload data files
                        </button>
                      </li>
                    )}
                    {isMissingContract && (
                      <li>
                        <button onClick={() => navigate('/contract')} className="underline hover:text-red-900">
                          Load or configure a contract
                        </button>
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
        <button onClick={calculate} className="btn-primary">
          Retry Calculation
        </button>
      </div>
    );
  }

  // -- Idle (should not stay here long due to auto-run) -------------------
  if (phase === 'idle' || !metrics) {
    return (
      <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
        <div className="rounded-xl bg-brand-50 p-4">
          <svg className="h-12 w-12 text-brand-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25v-.008zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007v-.008zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008v-.008zm2.498-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008v-.008zM8.25 6h7.5v2.25h-7.5V6zM12 2.25c-1.892 0-3.758.11-5.593.322C5.307 2.7 4.5 3.65 4.5 4.757V19.5a2.25 2.25 0 002.25 2.25h10.5a2.25 2.25 0 002.25-2.25V4.757c0-1.108-.806-2.057-1.907-2.185A48.507 48.507 0 0012 2.25z" />
          </svg>
        </div>
        <div>
          <h2>Ready to Calculate</h2>
          <p className="mt-1 text-sm text-gray-500">
            Load data and configure your contract, then run the pipeline.
          </p>
        </div>
        <button onClick={calculate} className="btn-primary">
          Run Calculation
        </button>
      </div>
    );
  }

  // -- Ready state: full dashboard ----------------------------------------
  const grossSavings = metrics.gross_savings ?? metrics.total_savings ?? 0;
  const sharedSavings = metrics.shared_savings_amount ?? metrics.shared_savings ?? 0;

  return (
    <div className="space-y-6">
      {/* ----- Reconciliation banner ----- */}
      {recon && recon.total_discrepancies > 0 && (
        <button
          type="button"
          onClick={goRecon}
          className="w-full rounded-xl border border-amber-200 bg-amber-50 px-6 py-4 text-left transition-colors hover:bg-amber-100"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <div>
                <span className="font-semibold text-amber-900">
                  {recon.total_discrepancies} Discrepancies Found
                </span>
                <span className="ml-3 text-sm text-amber-700">
                  Total financial impact: {formatCurrency(Math.abs(recon.financial_impact))}
                </span>
              </div>
            </div>
            <span className="flex items-center gap-1 text-sm font-medium text-amber-700">
              View Details
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </span>
          </div>
        </button>
      )}

      {/* ----- Page header ----- */}
      <div className="flex items-center justify-between">
        <div>
          <h1>Performance Results</h1>
          <p className="mt-1 text-sm text-gray-500">
            All numbers are clickable -- drill down to see the contract language, data, and code behind each calculation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={exportPipelineJson} className="btn-secondary" title="Export full pipeline result as JSON">
            <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Export JSON
          </button>
          <button onClick={calculate} className="btn-secondary">
            <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
            Recalculate
          </button>
        </div>
      </div>

      {/* ----- Top metric cards ----- */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          title="Attributed Population"
          value={formatNumber(metrics.attributed_population)}
          subtitle={`${formatNumber(metrics.member_months ?? 0)} member-months`}
          status="neutral"
          onClick={() => drillMetric('attributed_population')}
        />
        <MetricCard
          title="Quality Composite"
          value={formatPercent(metrics.quality_composite)}
          subtitle={metrics.quality_gate_passed ? 'Gate passed' : 'Below quality gate'}
          status={qualityStatus()}
          onClick={() => drillMetric('quality_composite')}
        />
        <MetricCard
          title="Actual PMPM"
          value={formatCurrency(metrics.actual_pmpm, 0)}
          subtitle={`Benchmark: ${formatCurrency(metrics.benchmark_pmpm, 0)}`}
          status={metrics.actual_pmpm < metrics.benchmark_pmpm ? 'green' : 'red'}
          onClick={() => drillMetric('actual_pmpm')}
          confidenceLow={
            metrics.confidence_low_pmpm != null
              ? formatCurrency(metrics.confidence_low_pmpm, 0)
              : undefined
          }
          confidenceHigh={
            metrics.confidence_high_pmpm != null
              ? formatCurrency(metrics.confidence_high_pmpm, 0)
              : undefined
          }
        />
        <MetricCard
          title="Projected Savings"
          value={formatCurrency(grossSavings, 0)}
          subtitle={
            grossSavings > 0
              ? `${((grossSavings / (metrics.benchmark_pmpm * (metrics.member_months ?? 1))) * 100).toFixed(1)}% of total cost`
              : 'No savings'
          }
          status={savingsStatus()}
          onClick={() => drillMetric('gross_savings')}
        />
        <MetricCard
          title="Settlement Amount"
          value={formatCurrency(sharedSavings, 0)}
          subtitle={
            metrics.msr_passed && metrics.quality_gate_passed
              ? 'All gates passed'
              : 'Gates not met'
          }
          status={settlementStatus()}
          onClick={() => drillMetric('shared_savings_amount')}
          gates={{
            msr: metrics.msr_passed ?? false,
            quality: metrics.quality_gate_passed ?? false,
          }}
        />
      </div>

      {/* ----- Cost chart ----- */}
      <CostChart
        benchmarkPmpm={metrics.benchmark_pmpm}
        actualPmpm={metrics.actual_pmpm}
        confidenceLow={metrics.confidence_low_pmpm}
        confidenceHigh={metrics.confidence_high_pmpm}
        onClick={() => drillStep(4)}
      />

      {/* ----- Quality scorecard ----- */}
      {qualityMeasures.length > 0 && (
        <QualityScorecard
          measures={qualityMeasures}
          compositeScore={metrics.quality_composite}
          onMeasureClick={(measureId) => drillMetric(`quality_${measureId}`)}
        />
      )}

      {/* ----- Pipeline steps summary ----- */}
      <div className="card">
        <div className="card-header">
          <h3>Pipeline Execution Summary</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { step: 1, label: 'Eligibility', icon: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z' },
              { step: 2, label: 'Attribution', icon: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5' },
              { step: 3, label: 'Quality', icon: 'M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z' },
              { step: 4, label: 'Cost', icon: 'M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
              { step: 5, label: 'Settlement', icon: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z' },
              { step: 6, label: 'Reconciliation', icon: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z' },
            ].map((s) => (
              <button
                key={s.step}
                type="button"
                onClick={() => drillStep(s.step)}
                className="flex flex-col items-center gap-2 rounded-lg border border-gray-100 p-3 text-center transition-all hover:border-brand-300 hover:bg-brand-50"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d={s.icon} />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-900">Step {s.step}</p>
                  <p className="text-[10px] text-gray-500">{s.label}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ----- Execution time footer ----- */}
      {executionTime != null && (
        <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>
            Pipeline executed in {executionTime.toLocaleString()}ms -- Every number above is traceable to its source data, contract language, and code.
          </span>
        </div>
      )}
    </div>
  );
}
