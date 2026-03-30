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

        {/* Platform vs Payer values side by side */}
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3">
            <p className="text-xs font-medium text-blue-600 mb-0.5">Platform Value</p>
            <p className="text-sm font-semibold text-blue-900">
              {discrepancy.platform_value != null ? String(discrepancy.platform_value) : '--'}
            </p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3">
            <p className="text-xs font-medium text-amber-600 mb-0.5">Payer Value</p>
            <p className="text-sm font-semibold text-amber-900">
              {discrepancy.payer_value != null ? String(discrepancy.payer_value) : '--'}
            </p>
          </div>
        </div>

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

        {/* Supporting Data References */}
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
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-indigo-900 mb-1">Resolution Recommendation</p>
              <p className="text-sm text-indigo-800 leading-relaxed">
                {resolveRecommendation(discrepancy)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Generate a resolution recommendation based on the discrepancy type.
 */
function resolveRecommendation(d: Discrepancy): string {
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
