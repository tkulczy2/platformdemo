import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  ErrorBar,
} from 'recharts';
import { formatCurrency } from '@/utils/formatters';

export interface CostChartProps {
  benchmarkPmpm: number;
  actualPmpm: number;
  confidenceLow?: number;
  confidenceHigh?: number;
  onClick?: () => void;
}

export default function CostChart({
  benchmarkPmpm,
  actualPmpm,
  confidenceLow,
  confidenceHigh,
  onClick,
}: CostChartProps) {
  const savings = benchmarkPmpm - actualPmpm;
  const savingsPositive = savings > 0;

  // Compute error bar values (distance from actual to low/high)
  const errorLow = confidenceLow != null ? actualPmpm - confidenceLow : 0;
  const errorHigh = confidenceHigh != null ? confidenceHigh - actualPmpm : 0;
  const hasCI = errorLow > 0 || errorHigh > 0;

  const data = [
    {
      name: 'Benchmark',
      value: benchmarkPmpm,
      errorLow: 0,
      errorHigh: 0,
    },
    {
      name: 'Actual PMPM',
      value: actualPmpm,
      errorLow: hasCI ? errorLow : 0,
      errorHigh: hasCI ? errorHigh : 0,
    },
  ];

  const maxVal = Math.max(
    benchmarkPmpm,
    confidenceHigh ?? actualPmpm,
  ) * 1.15;

  return (
    <div className="card overflow-hidden">
      <div className="card-header flex items-center justify-between">
        <h3>Cost Performance</h3>
        <div className="flex items-center gap-3">
          {savingsPositive ? (
            <span className="badge-success">
              Savings: {formatCurrency(savings, 2)} PMPM
            </span>
          ) : (
            <span className="badge-error">
              Overspend: {formatCurrency(Math.abs(savings), 2)} PMPM
            </span>
          )}
          {hasCI && (
            <span className="badge-info">Maturity-adjusted</span>
          )}
        </div>
      </div>

      <div
        className="card-body cursor-pointer transition-colors hover:bg-gray-50/50"
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(); }}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} barCategoryGap="35%" margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 13, fill: '#6b7280' }}
            />
            <YAxis
              domain={[0, maxVal]}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v.toLocaleString()}`}
              tick={{ fontSize: 12, fill: '#9ca3af' }}
              width={80}
            />
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), 'PMPM']}
              contentStyle={{
                borderRadius: 8,
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)',
                fontSize: 13,
              }}
            />
            {/* Reference line for benchmark */}
            <ReferenceLine
              y={benchmarkPmpm}
              stroke="#9ca3af"
              strokeDasharray="6 3"
              label={{
                value: `Benchmark: ${formatCurrency(benchmarkPmpm)}`,
                position: 'insideTopRight',
                fontSize: 11,
                fill: '#9ca3af',
              }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={80}>
              <Cell fill="#94a3b8" /> {/* Benchmark bar - gray */}
              <Cell fill={savingsPositive ? '#059669' : '#dc2626'} /> {/* Actual bar */}
              {hasCI && <ErrorBar dataKey="errorHigh" width={12} stroke="#6b7280" />}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Savings zone annotation */}
        {savingsPositive && (
          <div className="mt-2 flex items-center justify-center gap-2 text-sm">
            <div className="h-3 w-3 rounded-sm bg-emerald-100 ring-1 ring-emerald-300" />
            <span className="text-gray-500">
              Savings zone: {formatCurrency(savings)} PMPM
              ({((savings / benchmarkPmpm) * 100).toFixed(1)}% below benchmark)
            </span>
          </div>
        )}

        {hasCI && (
          <div className="mt-1 flex items-center justify-center gap-2 text-xs text-gray-400">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <span>
              Confidence interval: {formatCurrency(confidenceLow ?? actualPmpm)} -- {formatCurrency(confidenceHigh ?? actualPmpm)} (claims maturity adjustment applied)
            </span>
          </div>
        )}
      </div>

      <div className="card-body border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Click chart to drill down into cost calculation with full provenance.
        </p>
      </div>
    </div>
  );
}
