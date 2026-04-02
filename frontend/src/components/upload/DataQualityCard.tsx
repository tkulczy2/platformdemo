import { useState } from 'react';
import { FileQualityScore } from '@/types';
import { formatNumber, formatPercent, classNames } from '@/utils/formatters';

interface DataQualityCardProps {
  quality: FileQualityScore;
}

/** Human-friendly labels for file names. */
const FILE_LABELS: Record<string, string> = {
  'members.csv': 'Members',
  'providers.csv': 'Providers',
  'eligibility.csv': 'Eligibility',
  'claims_professional.csv': 'Professional Claims',
  'claims_facility.csv': 'Facility Claims',
  'claims_pharmacy.csv': 'Pharmacy Claims',
  'clinical_labs.csv': 'Lab Results',
  'clinical_screenings.csv': 'Screenings',
  'clinical_vitals.csv': 'Vitals',
};

function statusColor(score: number): 'green' | 'yellow' | 'red' {
  if (score >= 0.95) return 'green';
  if (score >= 0.90) return 'yellow';
  return 'red';
}

const DOT_CLASSES: Record<string, string> = {
  green: 'bg-emerald-500',
  yellow: 'bg-amber-500',
  red: 'bg-red-500',
};

const BAR_CLASSES: Record<string, string> = {
  green: 'bg-emerald-500',
  yellow: 'bg-amber-500',
  red: 'bg-red-500',
};

export default function DataQualityCard({ quality }: DataQualityCardProps) {
  const [expanded, setExpanded] = useState(false);
  const color = statusColor(quality.completeness);
  const label = FILE_LABELS[quality.file_name] ?? quality.file_name;
  const hasIssues = quality.issues.length > 0;

  return (
    <div className="card">
      <div className="card-body space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={classNames('inline-block h-2.5 w-2.5 rounded-full', DOT_CLASSES[color])} />
            <h3 className="text-sm font-semibold text-gray-900">{label}</h3>
          </div>
          <span className="text-xs text-gray-500 font-mono">{quality.file_name}</span>
        </div>

        {/* Row count */}
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-gray-500">Rows</span>
          <span className="font-medium text-gray-900">{formatNumber(quality.rows)}</span>
        </div>

        {/* Completeness bar */}
        <div>
          <div className="flex items-baseline justify-between text-sm mb-1">
            <span className="text-gray-500">Completeness</span>
            <span className="font-medium text-gray-900">{formatPercent(quality.completeness)}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
            <div
              className={classNames('h-full rounded-full transition-all', BAR_CLASSES[color])}
              style={{ width: `${Math.min(quality.completeness * 100, 100)}%` }}
            />
          </div>
        </div>

        {/* Quality score */}
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-gray-500">Quality Score</span>
          <span className="font-medium text-gray-900">{formatPercent(quality.quality_score)}</span>
        </div>

        {/* Issues toggle */}
        {hasIssues && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              <svg
                className={classNames(
                  'h-3.5 w-3.5 transition-transform',
                  expanded && 'rotate-90',
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              {quality.issues.length} issue{quality.issues.length !== 1 ? 's' : ''} found
            </button>

            {expanded && (
              <ul className="mt-2 space-y-1.5">
                {quality.issues.map((issue, idx) => {
                  const severity = issueSeverity(issue);
                  return (
                    <li key={idx} className="flex items-start gap-2 text-xs">
                      <span
                        className={classNames(
                          severity === 'error' && 'badge-error',
                          severity === 'warning' && 'badge-warning',
                          severity === 'info' && 'badge-info',
                        )}
                      >
                        {severity}
                      </span>
                      <span className="text-gray-700 leading-tight">{issue}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Derive a severity from the issue text (heuristic). */
function issueSeverity(issue: string): 'error' | 'warning' | 'info' {
  const lower = issue.toLowerCase();
  if (lower.includes('missing') || lower.includes('invalid') || lower.includes('error')) {
    return 'error';
  }
  if (lower.includes('gap') || lower.includes('duplicate') || lower.includes('conflict')) {
    return 'warning';
  }
  return 'info';
}
