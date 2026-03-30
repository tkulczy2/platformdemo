import { classNames } from '@/utils/formatters';

export type MetricStatus = 'green' | 'yellow' | 'red' | 'neutral';

export interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  status?: MetricStatus;
  onClick?: () => void;
  confidenceLow?: string;
  confidenceHigh?: string;
  payer?: { label: string; delta: string };
  gates?: { msr: boolean; quality: boolean };
}

const STATUS_STYLES: Record<MetricStatus, { border: string; accent: string; bg: string }> = {
  green: {
    border: 'border-emerald-200 hover:border-emerald-400',
    accent: 'text-emerald-600',
    bg: 'bg-emerald-50',
  },
  yellow: {
    border: 'border-amber-200 hover:border-amber-400',
    accent: 'text-amber-600',
    bg: 'bg-amber-50',
  },
  red: {
    border: 'border-red-200 hover:border-red-400',
    accent: 'text-red-600',
    bg: 'bg-red-50',
  },
  neutral: {
    border: 'border-gray-200 hover:border-brand-400',
    accent: 'text-brand-600',
    bg: 'bg-brand-50',
  },
};

export default function MetricCard({
  title,
  value,
  subtitle,
  status = 'neutral',
  onClick,
  confidenceLow,
  confidenceHigh,
  payer,
  gates,
}: MetricCardProps) {
  const s = STATUS_STYLES[status];

  return (
    <button
      type="button"
      onClick={onClick}
      className={classNames(
        'card group relative flex flex-col items-start gap-1 p-5 text-left transition-all',
        'hover:shadow-md cursor-pointer',
        s.border,
      )}
    >
      {/* Title */}
      <span className="metric-label">{title}</span>

      {/* Value */}
      <span className="metric-value">{value}</span>

      {/* Confidence band */}
      {confidenceLow && confidenceHigh && (
        <span className="text-xs text-gray-400">
          CI: {confidenceLow} -- {confidenceHigh}
        </span>
      )}

      {/* Subtitle */}
      {subtitle && (
        <span className={classNames('text-sm font-medium', s.accent)}>{subtitle}</span>
      )}

      {/* Payer comparison */}
      {payer && (
        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          <span>Payer: {payer.label}</span>
          <span className="font-semibold text-gray-700">| {payer.delta}</span>
        </div>
      )}

      {/* Gate status icons */}
      {gates && (
        <div className="mt-1.5 flex items-center gap-3 text-xs">
          <span className="inline-flex items-center gap-1">
            {gates.msr ? (
              <svg className="h-3.5 w-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="h-3.5 w-3.5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            )}
            <span className={gates.msr ? 'text-emerald-700' : 'text-red-700'}>MSR</span>
          </span>
          <span className="inline-flex items-center gap-1">
            {gates.quality ? (
              <svg className="h-3.5 w-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="h-3.5 w-3.5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            )}
            <span className={gates.quality ? 'text-emerald-700' : 'text-red-700'}>Quality Gate</span>
          </span>
        </div>
      )}

      {/* Drill-down affordance */}
      <span className="absolute right-3 top-3 text-gray-300 opacity-0 transition-opacity group-hover:opacity-100">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
        </svg>
      </span>
      <span className="absolute inset-x-0 bottom-0 h-0.5 scale-x-0 rounded-b-xl bg-brand-500 transition-transform group-hover:scale-x-100" />
    </button>
  );
}
