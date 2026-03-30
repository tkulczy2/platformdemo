import { classNames, formatPercent, formatNumber } from '@/utils/formatters';
import type { QualityMeasure } from '@/types';

export interface QualityScorecardProps {
  measures: QualityMeasure[];
  compositeScore: number;
  onMeasureClick: (measureId: string) => void;
}

function rateColor(rate: number): string {
  // Rates come as percentages (e.g. 80.93), not decimals
  if (rate >= 75) return 'text-emerald-700 bg-emerald-50';
  if (rate >= 50) return 'text-amber-700 bg-amber-50';
  return 'text-red-700 bg-red-50';
}

function starDisplay(stars: number): string {
  return '\u2605'.repeat(Math.round(stars)) + '\u2606'.repeat(5 - Math.round(stars));
}

export default function QualityScorecard({
  measures,
  compositeScore,
  onMeasureClick,
}: QualityScorecardProps) {
  return (
    <div className="card overflow-hidden">
      <div className="card-header flex items-center justify-between">
        <h3>Quality Scorecard</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Composite:</span>
          <span
            className={classNames(
              'inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-bold',
              rateColor(compositeScore),
            )}
          >
            {formatPercent(compositeScore)}
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th className="table-header">Measure</th>
              <th className="table-header text-right">Rate</th>
              <th className="table-header text-right">Stars</th>
              <th className="table-header text-right">Numerator</th>
              <th className="table-header text-right">Denominator</th>
              <th className="table-header text-right">Exclusions</th>
              <th className="table-header text-right">Eligible</th>
              <th className="table-header text-right">Weight</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {measures.map((m) => (
              <tr
                key={m.measure_id}
                onClick={() => onMeasureClick(m.measure_id)}
                className="cursor-pointer transition-colors hover:bg-gray-50"
              >
                <td className="table-cell font-medium text-gray-900">{m.measure_name}</td>
                <td className="table-cell text-right">
                  <span
                    className={classNames(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                      rateColor(m.rate),
                    )}
                  >
                    {formatPercent(m.rate)}
                  </span>
                </td>
                <td className="table-cell text-right text-amber-500 tracking-tight text-sm">
                  {starDisplay(m.star_rating)}
                </td>
                <td className="table-cell text-right font-mono text-xs">
                  {formatNumber(m.numerator)}
                </td>
                <td className="table-cell text-right font-mono text-xs">
                  {formatNumber(m.denominator)}
                </td>
                <td className="table-cell text-right font-mono text-xs">
                  {formatNumber(m.exclusions)}
                </td>
                <td className="table-cell text-right font-mono text-xs">
                  {formatNumber(m.eligible)}
                </td>
                <td className="table-cell text-right font-mono text-xs">
                  {formatPercent(m.weight, 0)}
                </td>
              </tr>
            ))}
          </tbody>

          {/* Composite summary row */}
          <tfoot>
            <tr className="border-t-2 border-gray-200 bg-gray-50/50">
              <td className="table-cell font-semibold text-gray-900">Composite Score</td>
              <td className="table-cell text-right">
                <span
                  className={classNames(
                    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold',
                    rateColor(compositeScore),
                  )}
                >
                  {formatPercent(compositeScore)}
                </span>
              </td>
              <td className="table-cell" />
              <td className="table-cell text-right font-mono text-xs font-semibold">
                {formatNumber(measures.reduce((s, m) => s + m.numerator, 0))}
              </td>
              <td className="table-cell text-right font-mono text-xs font-semibold">
                {formatNumber(measures.reduce((s, m) => s + m.denominator, 0))}
              </td>
              <td className="table-cell text-right font-mono text-xs font-semibold">
                {formatNumber(measures.reduce((s, m) => s + m.exclusions, 0))}
              </td>
              <td className="table-cell text-right font-mono text-xs font-semibold">
                {formatNumber(measures.reduce((s, m) => s + m.eligible, 0))}
              </td>
              <td className="table-cell text-right font-mono text-xs font-semibold">100%</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="card-body border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Click any measure row to drill down into member-level detail with full provenance.
        </p>
      </div>
    </div>
  );
}
