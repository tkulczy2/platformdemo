import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, formatNumber, formatPercent, classNames } from '@/utils/formatters';
import { getSurveillanceProjections } from '@/api/client';

interface Projection {
  scenario_name: string;
  projected_attributed_count: number;
  projected_churn_rate: number;
  projected_shared_savings: number;
  projected_quality_composite: number;
  projected_quality_bonus: number;
  projected_total_settlement: number;
  key_assumptions: string[];
}

const SCENARIO_LABELS: Record<string, string> = {
  current_trajectory: 'Current Trajectory',
  with_intervention: 'With Intervention',
  worst_case: 'Worst Case',
};

const SCENARIO_COLORS: Record<string, string> = {
  current_trajectory: '#475569',
  with_intervention: '#059669',
  worst_case: '#dc2626',
};

export default function ProjectionView() {
  const [projections, setProjections] = useState<Projection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = (await getSurveillanceProjections()) as unknown as Projection[];
        setProjections(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading projections...</div>;
  if (error) return <div className="py-12 text-center text-red-600">{error}</div>;
  if (projections.length === 0) return null;

  const chartData = projections.map((p) => ({
    name: SCENARIO_LABELS[p.scenario_name] || p.scenario_name,
    settlement: p.projected_total_settlement,
    fill: SCENARIO_COLORS[p.scenario_name] || '#475569',
  }));

  const a = projections.find((p) => p.scenario_name === 'current_trajectory');
  const b = projections.find((p) => p.scenario_name === 'with_intervention');
  const c = projections.find((p) => p.scenario_name === 'worst_case');

  const interventionDelta = b && a ? b.projected_total_settlement - a.projected_total_settlement : 0;
  const downsideDelta = a && c ? a.projected_total_settlement - c.projected_total_settlement : 0;

  return (
    <div className="space-y-6">
      {/* Chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Year-End Settlement Projection</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(value: number) => [formatCurrency(value), 'Total Settlement']} />
            <Bar dataKey="settlement" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, i) => (
                <rect key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-4 flex items-center justify-center gap-6 text-xs">
          {interventionDelta > 0 && (
            <span className="text-green-700">
              Targeted intervention adds <strong>{formatCurrency(interventionDelta)}</strong> to projected settlement
            </span>
          )}
          {downsideDelta > 0 && (
            <span className="text-red-700">
              Downside risk without intervention: <strong>{formatCurrency(downsideDelta)}</strong>
            </span>
          )}
        </div>
      </div>

      {/* Three-column comparison */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {projections.map((p) => (
          <div
            key={p.scenario_name}
            className={classNames(
              'rounded-xl border p-6',
              p.scenario_name === 'with_intervention' ? 'border-green-200 bg-green-50'
                : p.scenario_name === 'worst_case' ? 'border-red-200 bg-red-50'
                : 'border-gray-200 bg-white',
            )}
          >
            <h4 className={classNames(
              'text-sm font-semibold',
              p.scenario_name === 'with_intervention' ? 'text-green-900'
                : p.scenario_name === 'worst_case' ? 'text-red-900'
                : 'text-gray-900',
            )}>
              {SCENARIO_LABELS[p.scenario_name] || p.scenario_name}
            </h4>

            <div className="mt-4 space-y-3">
              <MetricRow label="Attributed Count" value={formatNumber(p.projected_attributed_count)} />
              <MetricRow label="Churn Rate" value={formatPercent(p.projected_churn_rate)} />
              <MetricRow label="Shared Savings" value={formatCurrency(p.projected_shared_savings)} />
              <MetricRow label="Quality Composite" value={formatPercent(p.projected_quality_composite)} />
              <MetricRow label="Quality Bonus" value={formatCurrency(p.projected_quality_bonus)} />
              <div className="border-t border-gray-200 pt-2">
                <MetricRow
                  label="Total Settlement"
                  value={formatCurrency(p.projected_total_settlement)}
                  bold
                />
              </div>
            </div>

            <div className="mt-4">
              <div className="text-xs font-medium text-gray-500 mb-1">Key Assumptions</div>
              <ul className="text-xs text-gray-600 space-y-1">
                {p.key_assumptions.map((a, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-400 mt-0.5">•</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {/* Narrative */}
      {a && b && c && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6">
          <p className="text-sm text-slate-700 leading-relaxed">
            Based on current attribution trends, the ACO is projected to receive{' '}
            <strong>{formatCurrency(a.projected_total_settlement)}</strong> in total settlement at year-end.
            If the highest-ROI retention actions are executed at a total intervention cost,
            projected settlement increases to <strong>{formatCurrency(b.projected_total_settlement)}</strong> —
            a net gain of <strong>{formatCurrency(interventionDelta)}</strong>.
            In a worst-case scenario where all at-risk members are lost, settlement drops to{' '}
            <strong>{formatCurrency(c.projected_total_settlement)}</strong>.
            The retention program pays for itself{' '}
            <strong>{(interventionDelta / Math.max(1, b.projected_total_settlement - a.projected_total_settlement)).toFixed(0) || ''}
            </strong> times over.
          </p>
        </div>
      )}
    </div>
  );
}

function MetricRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={classNames('tabular-nums', bold ? 'text-sm font-semibold text-gray-900' : 'text-sm text-gray-900')}>
        {value}
      </span>
    </div>
  );
}
