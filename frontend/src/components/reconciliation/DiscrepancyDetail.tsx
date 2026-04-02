import { Discrepancy } from '@/types';
import { formatCurrency, classNames } from '@/utils/formatters';

interface DiscrepancyDetailProps {
  discrepancy: Discrepancy;
}

const CATEGORY_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  attribution: { label: 'Attribution', bg: 'bg-blue-50', text: 'text-blue-800' },
  quality: { label: 'Quality', bg: 'bg-purple-50', text: 'text-purple-800' },
  cost: { label: 'Cost', bg: 'bg-orange-50', text: 'text-orange-800' },
};

const SUBCATEGORY_LABELS: Record<string, string> = {
  data_difference: 'Data Difference',
  methodology_difference: 'Methodology Difference',
  timing_difference: 'Timing Difference',
  specification_ambiguity: 'Specification Ambiguity',
  platform_only: 'Platform Only',
  payer_only: 'Payer Only',
  different_provider: 'Different Provider',
  ehr_only_data: 'EHR-Only Data',
  payer_exclusion: 'Payer Exclusion',
  screening_conflict: 'Screening Conflict',
  runout_timing: 'Run-out Timing',
  amount_difference: 'Amount Difference',
};

export default function DiscrepancyDetail({ discrepancy }: DiscrepancyDetailProps) {
  const cat = CATEGORY_CONFIG[discrepancy.category] ?? {
    label: discrepancy.category,
    bg: 'bg-gray-50',
    text: 'text-gray-800',
  };

  const impactIsPositive = discrepancy.financial_impact > 0;
  const valueLabel = discrepancy.metric_label || 'Value';

  return (
    <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
      {/* Header */}
      <div className="border-b border-gray-100 bg-gray-50 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={classNames('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', cat.bg, cat.text)}>
            {cat.label}
          </span>
          <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
            {SUBCATEGORY_LABELS[discrepancy.subcategory] ?? discrepancy.subcategory}
          </span>
          <span className="text-xs text-gray-500 font-mono">{discrepancy.id}</span>
        </div>
        <div className={classNames(
          'text-sm font-semibold',
          impactIsPositive ? 'text-emerald-700' : 'text-red-700',
        )}>
          {impactIsPositive ? '+' : ''}{formatCurrency(discrepancy.financial_impact)}
        </div>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Description / Explanation */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">Explanation</h4>
          <p className="text-sm text-gray-700 leading-relaxed">{discrepancy.description}</p>
        </div>

        {/* Platform vs Payer values side by side — with descriptive labels */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3">
            <p className="text-xs font-medium text-blue-600 mb-0.5">Platform: {valueLabel}</p>
            <p className="text-sm font-semibold text-blue-900">
              {discrepancy.platform_value != null ? String(discrepancy.platform_value) : '--'}
            </p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3">
            <p className="text-xs font-medium text-amber-600 mb-0.5">Payer: {valueLabel}</p>
            <p className="text-sm font-semibold text-amber-900">
              {discrepancy.payer_value != null ? String(discrepancy.payer_value) : '--'}
            </p>
          </div>
        </div>

        {/* Quality measure detail breakdown */}
        {discrepancy.detail && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Measure Component Breakdown</h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border border-blue-100 bg-blue-50/30 p-2.5">
                <p className="text-[10px] font-medium text-blue-600 uppercase mb-1">Platform</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Numerator</span>
                  <span className="font-semibold text-gray-900">{discrepancy.detail.platform_numerator}</span>
                </div>
                <div className="flex items-center justify-between text-xs mt-0.5">
                  <span className="text-gray-600">Denominator</span>
                  <span className="font-semibold text-gray-900">{discrepancy.detail.platform_denominator}</span>
                </div>
              </div>
              <div className="rounded-md border border-amber-100 bg-amber-50/30 p-2.5">
                <p className="text-[10px] font-medium text-amber-600 uppercase mb-1">Payer</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Numerator</span>
                  <span className="font-semibold text-gray-900">{discrepancy.detail.payer_numerator}</span>
                </div>
                <div className="flex items-center justify-between text-xs mt-0.5">
                  <span className="text-gray-600">Denominator</span>
                  <span className="font-semibold text-gray-900">{discrepancy.detail.payer_denominator}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Member ID */}
        {discrepancy.member_id && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">Affected Member</h4>
            <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-mono font-medium text-gray-700">
              {discrepancy.member_id}
            </span>
          </div>
        )}

        {/* Root Cause */}
        {discrepancy.root_cause && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1.5">Root Cause</h4>
            <p className="text-sm text-gray-700 leading-relaxed">{discrepancy.root_cause}</p>
          </div>
        )}

        {/* Governing Contract Language */}
        {discrepancy.relevant_clauses && discrepancy.relevant_clauses.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                Governing Contract Language
              </span>
            </h4>
            <div className="space-y-2">
              {discrepancy.relevant_clauses.map((clause) => (
                <div key={clause.clause_id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
                  <div className="flex items-start gap-2">
                    <span className="inline-flex items-center rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-mono font-semibold text-slate-700 flex-shrink-0">
                      {clause.clause_id}
                    </span>
                    <p className="text-xs text-slate-700 leading-relaxed">{clause.clause_text}</p>
                  </div>
                  {clause.interpretation && (
                    <p className="mt-1.5 text-xs text-slate-500 italic leading-relaxed pl-2 border-l-2 border-slate-200">
                      {clause.interpretation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data Sources */}
        {discrepancy.data_sources && discrepancy.data_sources.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
              <span className="inline-flex items-center gap-1.5">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                </svg>
                Key Data Sources
              </span>
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {discrepancy.data_sources.map((file) => (
                <span key={file} className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-mono text-gray-600">
                  {file}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Supporting Data References (row-level) */}
        {discrepancy.data_references && discrepancy.data_references.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Supporting Data</h4>
            <div className="space-y-2">
              {discrepancy.data_references.map((ref, idx) => (
                <div key={idx} className="rounded-md border border-gray-200 bg-gray-50 p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-medium text-gray-600">{ref.file}</span>
                    <span className="text-xs text-gray-400">Row {ref.row_index}</span>
                  </div>
                  {ref.description && (
                    <p className="text-xs text-gray-500 mb-1.5">{ref.description}</p>
                  )}
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    {Object.entries(ref.columns).map(([key, val]) => (
                      <span key={key} className="text-xs">
                        <span className="text-gray-500">{key}:</span>{' '}
                        <span className="font-mono text-gray-700">{String(val ?? 'null')}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Financial Impact callout */}
        <div className={classNames(
          'rounded-lg border px-4 py-3 flex items-center justify-between',
          impactIsPositive
            ? 'border-emerald-200 bg-emerald-50'
            : 'border-red-200 bg-red-50',
        )}>
          <div>
            <p className={classNames(
              'text-xs font-semibold uppercase tracking-wider',
              impactIsPositive ? 'text-emerald-600' : 'text-red-600',
            )}>
              Financial Impact
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {impactIsPositive
                ? 'Platform identifies higher value than payer report'
                : 'Platform identifies lower value than payer report'}
            </p>
          </div>
          <span className={classNames(
            'text-lg font-bold',
            impactIsPositive ? 'text-emerald-700' : 'text-red-700',
          )}>
            {impactIsPositive ? '+' : ''}{formatCurrency(discrepancy.financial_impact)}
          </span>
        </div>

        {/* Resolution Recommendation */}
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
          <div className="flex items-start gap-2.5">
            <svg className="h-5 w-5 text-indigo-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5.002 5.002 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-indigo-900 mb-1">Resolution Recommendation</p>
              <p className="text-sm text-indigo-800 leading-relaxed">
                {discrepancy.resolution_recommendation || fallbackRecommendation(discrepancy)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Fallback recommendation if the backend doesn't provide one.
 */
function fallbackRecommendation(d: Discrepancy): string {
  if (d.subcategory === 'platform_only' || d.subcategory === 'payer_only') {
    return `Review the attribution methodology to determine whether the ${d.subcategory === 'platform_only' ? 'platform' : 'payer'} correctly included or excluded this member. Compare qualifying visit counts and provider assignment logic against the contract language.`;
  }
  if (d.subcategory === 'different_provider') {
    return 'Both parties attributed this member but to different providers. Review the tiebreaker logic and qualifying visit counts for each provider to determine the correct assignment.';
  }
  if (d.subcategory === 'ehr_only_data') {
    return 'The platform used EHR/clinical data that the payer may not have access to. Confirm that the contract allows supplemental data submission and verify the data was submitted within the required timeframe.';
  }
  if (d.subcategory === 'payer_exclusion') {
    return 'The payer applied an exclusion that the platform did not. Review the exclusion criteria in the contract and verify the clinical evidence supporting the exclusion.';
  }
  if (d.subcategory === 'screening_conflict') {
    return 'Claims and clinical data show conflicting screening results. Apply the conflict resolution rule specified in the contract (e.g., most recent clinical value) and verify both data sources.';
  }
  if (d.subcategory === 'runout_timing') {
    return 'This discrepancy is likely due to claims run-out timing differences. Compare the data cut-off dates and consider re-running with aligned run-out periods.';
  }
  if (d.subcategory === 'amount_difference') {
    return 'The claim amounts differ between platform and payer data. Review the specific claims for this member and verify whether allowed vs. paid amounts are being used consistently.';
  }
  return `Investigate the ${d.category} discrepancy by reviewing the underlying data sources and contract language. Compare the calculation methodology used by both parties.`;
}
