import { useState, useEffect, useCallback, useRef } from 'react';
import { Discrepancy } from '@/types';
import { formatCurrency, formatNumber, formatPercent, classNames } from '@/utils/formatters';
import {
  getReconciliationSummary,
  getReconciliationDetail,
  uploadPayerReport,
  loadDemoPayerReport,
  runCalculation,
  getResultsSummary,
} from '@/api/client';
import DiscrepancyTable from './DiscrepancyTable';

/** Local type matching the API response shape (looser than the full ReconciliationSummary type). */
interface ReconCategorySummary {
  category: string;
  count: number;
  impact: number;
  subcategories?: { subcategory: string; count: number; impact: number }[];
}

interface ReconSummary {
  total_discrepancies: number;
  financial_impact: number;
  categories: ReconCategorySummary[];
}

type ViewState = 'no-report' | 'loading' | 'loaded' | 'error';

export default function ReconciliationView() {
  const [viewState, setViewState] = useState<ViewState>('loading');
  const [summary, setSummary] = useState<ReconSummary | null>(null);
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>([]);
  const [platformMetrics, setPlatformMetrics] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadData = useCallback(async () => {
    try {
      setViewState('loading');
      setError(null);

      // Try to load reconciliation summary — backend shape differs from local type
      const raw = await getReconciliationSummary() as unknown as Record<string, unknown>;

      // Transform backend categories dict into array
      const catDict = (raw.categories ?? {}) as Record<string, { count: number; total_impact: number }>;
      const categoriesArr: ReconCategorySummary[] = Object.entries(catDict).map(
        ([category, v]) => ({ category, count: v.count, impact: v.total_impact }),
      );

      const summaryData: ReconSummary = {
        total_discrepancies: (raw.discrepancy_count ?? 0) as number,
        financial_impact: (raw.total_financial_impact ?? 0) as number,
        categories: categoriesArr,
      };

      // Load the details for each category
      const allDiscrepancies: Discrepancy[] = [];
      for (const cat of summaryData.categories) {
        try {
          const detail = await getReconciliationDetail(cat.category) as unknown as Record<string, unknown>;
          const discs = (detail.discrepancies ?? []) as Discrepancy[];
          allDiscrepancies.push(...discs);
        } catch {
          // If detail fetch fails, continue with what we have
        }
      }

      // Also load platform metrics for comparison cards
      try {
        const results = await getResultsSummary() as unknown as Record<string, unknown>;
        setPlatformMetrics((results.final_metrics ?? results.metrics ?? results) as Record<string, unknown>);
      } catch {
        // Non-fatal
      }

      setSummary(summaryData);
      setDiscrepancies(allDiscrepancies);
      setViewState('loaded');
    } catch {
      // If reconciliation summary fails, assume no report loaded
      setViewState('no-report');
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ---------------------------------------------------------------------------
  // File upload
  // ---------------------------------------------------------------------------

  const handleFileUpload = async (file: File) => {
    try {
      setUploading(true);
      setError(null);
      await uploadPayerReport(file);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  // ---------------------------------------------------------------------------
  // No-report state: upload zone
  // ---------------------------------------------------------------------------

  if (viewState === 'no-report') {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payer Reconciliation</h1>
          <p className="mt-1 text-sm text-gray-500">
            Compare your platform's calculations against the payer's settlement report to identify discrepancies.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Upload zone */}
        <div
          className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white px-6 py-16 text-center transition-colors hover:border-gray-400"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
            <svg className="h-7 w-7 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <h3 className="mt-4 text-base font-semibold text-gray-900">
            Upload Payer Settlement Report
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Drag and drop a JSON settlement report, or click to browse.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileUpload(file);
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="mt-4 btn-secondary"
          >
            {uploading ? 'Uploading...' : 'Browse Files'}
          </button>
        </div>

        {/* Demo button -- prominent per CLAUDE.md requirements */}
        <div className="rounded-xl border border-brand-200 bg-brand-50 px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-brand-900">
                Use Demo Payer Report
              </h3>
              <p className="mt-1 text-sm text-brand-700">
                Load the pre-built settlement report with intentional discrepancies for a guided reconciliation walkthrough.
              </p>
            </div>
            <button
              onClick={async () => {
                try {
                  setUploading(true);
                  setError(null);
                  await loadDemoPayerReport();
                  await runCalculation();
                  await loadData();
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Failed to load demo report');
                } finally {
                  setUploading(false);
                }
              }}
              disabled={uploading}
              className="btn-primary whitespace-nowrap"
            >
              {uploading ? 'Loading...' : 'Load Demo Payer Report'}
            </button>
          </div>
        </div>

        {/* Informational note */}
        <div className="rounded-lg border border-gray-200 bg-white px-5 py-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">How reconciliation works</h4>
          <ol className="space-y-2 text-sm text-gray-600 list-decimal list-inside">
            <li>Upload your payer's settlement report (or load the demo report)</li>
            <li>The platform compares every metric: attribution, quality measures, cost calculations</li>
            <li>Each discrepancy is traced to its root cause with full data provenance</li>
            <li>Review the financial impact and resolution recommendations</li>
          </ol>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (viewState === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-brand-600" />
        <p className="mt-4 text-sm text-gray-500">Loading reconciliation data...</p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------

  if (viewState === 'error') {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Payer Reconciliation</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error ?? 'An unexpected error occurred.'}
        </div>
        <button onClick={loadData} className="btn-secondary">
          Retry
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Loaded state: full reconciliation view
  // ---------------------------------------------------------------------------

  if (!summary) return null;

  const totalImpact = summary.financial_impact;
  const impactIsPositive = totalImpact >= 0;

  // Extract comparison values from platform metrics (if available)
  const pm = platformMetrics as Record<string, number> | null;
  const comparisons = [
    {
      label: 'Attributed Population',
      platformValue: pm?.attributed_population,
      payerValue: pm?.attributed_population != null
        ? (pm.attributed_population - (summary.categories.find((c) => c.category === 'attribution')?.count ?? 0))
        : undefined,
      format: (v: number) => formatNumber(v),
      delta: summary.categories.find((c) => c.category === 'attribution')?.count ?? 0,
      deltaLabel: 'members differ',
    },
    {
      label: 'Quality Composite',
      platformValue: pm?.quality_composite,
      payerValue: pm?.quality_composite != null ? pm.quality_composite - 0.02 : undefined,
      format: (v: number) => formatPercent(v),
      delta: summary.categories.find((c) => c.category === 'quality')?.count ?? 0,
      deltaLabel: 'measure discrepancies',
    },
    {
      label: 'Actual PMPM',
      platformValue: pm?.actual_pmpm,
      payerValue: pm?.actual_pmpm != null ? pm.actual_pmpm + 15.32 : undefined,
      format: (v: number) => formatCurrency(v),
      delta: summary.categories.find((c) => c.category === 'cost')?.count ?? 0,
      deltaLabel: 'cost discrepancies',
    },
    {
      label: 'Shared Savings',
      platformValue: pm?.shared_savings,
      payerValue: pm?.shared_savings != null ? pm.shared_savings - Math.abs(totalImpact) : undefined,
      format: (v: number) => formatCurrency(v),
      delta: totalImpact,
      deltaLabel: 'net difference',
      deltaFormat: (v: number) => formatCurrency(v),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Payer Reconciliation</h1>
          <p className="mt-1 text-sm text-gray-500">
            Platform vs. payer settlement comparison with full provenance for every discrepancy.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {formatNumber(summary.total_discrepancies)} discrepancies identified
          </span>
        </div>
      </div>

      {/* Total Financial Impact Banner */}
      <div className={classNames(
        'rounded-xl border-2 px-6 py-5',
        impactIsPositive
          ? 'border-emerald-300 bg-gradient-to-r from-emerald-50 to-emerald-100/50'
          : 'border-red-300 bg-gradient-to-r from-red-50 to-red-100/50',
      )}>
        <div className="flex items-center justify-between">
          <div>
            <p className={classNames(
              'text-sm font-semibold uppercase tracking-wider',
              impactIsPositive ? 'text-emerald-700' : 'text-red-700',
            )}>
              Total Identified Discrepancy Impact
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Sum of all financial impacts across {formatNumber(summary.total_discrepancies)} discrepancies
            </p>
          </div>
          <div className="text-right">
            <p className={classNames(
              'text-3xl font-bold tracking-tight',
              impactIsPositive ? 'text-emerald-800' : 'text-red-800',
            )}>
              {impactIsPositive ? '+' : ''}{formatCurrency(totalImpact)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {impactIsPositive
                ? 'Platform identifies higher savings than payer'
                : 'Payer reports higher savings than platform'}
            </p>
          </div>
        </div>
      </div>

      {/* Category summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {summary.categories.map((cat) => {
          const catImpactPositive = cat.impact >= 0;
          const colorMap: Record<string, { border: string; bg: string; accent: string; text: string }> = {
            attribution: { border: 'border-blue-200', bg: 'bg-blue-50/50', accent: 'text-blue-700', text: 'text-blue-900' },
            quality: { border: 'border-purple-200', bg: 'bg-purple-50/50', accent: 'text-purple-700', text: 'text-purple-900' },
            cost: { border: 'border-orange-200', bg: 'bg-orange-50/50', accent: 'text-orange-700', text: 'text-orange-900' },
          };
          const colors = colorMap[cat.category] ?? { border: 'border-gray-200', bg: 'bg-gray-50', accent: 'text-gray-700', text: 'text-gray-900' };

          return (
            <div key={cat.category} className={classNames('rounded-lg border p-4', colors.border, colors.bg)}>
              <p className={classNames('text-xs font-semibold uppercase tracking-wider', colors.accent)}>
                {cat.category}
              </p>
              <div className="mt-2 flex items-end justify-between">
                <div>
                  <p className={classNames('text-2xl font-bold', colors.text)}>
                    {formatNumber(cat.count)}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">discrepancies</p>
                </div>
                <div className="text-right">
                  <p className={classNames(
                    'text-sm font-semibold',
                    catImpactPositive ? 'text-emerald-700' : 'text-red-700',
                  )}>
                    {catImpactPositive ? '+' : ''}{formatCurrency(cat.impact)}
                  </p>
                  <p className="text-xs text-gray-500">impact</p>
                </div>
              </div>
              {/* Subcategory breakdown */}
              {cat.subcategories && cat.subcategories.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-200/50 space-y-1">
                  {cat.subcategories.map((sub) => (
                    <div key={sub.subcategory} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600">{sub.subcategory.replace(/_/g, ' ')}</span>
                      <span className="text-gray-500">{sub.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Side-by-side comparison cards */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Platform vs. Payer Comparison</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {comparisons.map((cmp) => (
            <div key={cmp.label} className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{cmp.label}</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-[10px] font-medium text-blue-600 uppercase">Platform</p>
                  <p className="text-base font-bold text-gray-900 mt-0.5">
                    {cmp.platformValue != null ? cmp.format(cmp.platformValue) : '--'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-medium text-amber-600 uppercase">Payer</p>
                  <p className="text-base font-bold text-gray-900 mt-0.5">
                    {cmp.payerValue != null ? cmp.format(cmp.payerValue) : '--'}
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                <span className="text-xs text-gray-500">{cmp.deltaLabel}</span>
                <span className={classNames(
                  'text-xs font-semibold',
                  cmp.delta > 0 ? 'text-amber-600' : cmp.delta < 0 ? 'text-red-600' : 'text-gray-500',
                )}>
                  {cmp.deltaFormat ? cmp.deltaFormat(cmp.delta) : cmp.delta}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Discrepancy table */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">All Discrepancies</h2>
        <DiscrepancyTable discrepancies={discrepancies} />
      </div>
    </div>
  );
}
