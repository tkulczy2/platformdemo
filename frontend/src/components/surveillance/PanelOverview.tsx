import { useState, useEffect } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Line, Area, Bar } from 'recharts';
import { formatCurrency, formatNumber, formatPercent, classNames } from '@/utils/formatters';
import { getSurveillanceOverview, getSurveillanceChanges } from '@/api/client';

interface Snapshot {
  month: string;
  total_attributed: number;
  new_attributions: number;
  lost_attributions: number;
  net_change: number;
  churn_rate: number;
  cumulative_financial_impact: number;
}

interface OverviewData {
  current_attributed: number;
  current_at_risk: number;
  current_financial_exposure: number;
  monthly_snapshots: Snapshot[];
  churn_by_quarter: Record<string, { new: number; lost: number; net: number }>;
  net_change_ytd: number;
  net_change_pct_ytd: number;
  narrative_markers: Record<string, unknown>;
}

interface ChangeEvent {
  event_id: string;
  member_id: string;
  event_month: string;
  event_type: string;
  change_classification: string;
  reason: string;
  financial_impact: { total_impact: number };
  prior_provider?: { name: string };
  new_provider?: { name: string };
}

export default function PanelOverview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [events, setEvents] = useState<ChangeEvent[]>([]);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [overview, changes] = await Promise.all([
          getSurveillanceOverview() as unknown as Promise<OverviewData>,
          getSurveillanceChanges({ limit: 200 }),
        ]);
        setData(overview);
        setEvents((changes as { events: ChangeEvent[] }).events || []);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading surveillance data...</div>;
  if (error) return <div className="py-12 text-center text-red-600">{error}</div>;
  if (!data) return null;

  const chartData = data.monthly_snapshots.map((s) => ({
    month: s.month.slice(5),
    label: new Date(s.month + '-01').toLocaleDateString('en-US', { month: 'short' }),
    total: s.total_attributed,
    new: s.new_attributions,
    lost: -s.lost_attributions,
    net: s.net_change,
  }));

  const filteredEvents = selectedMonth
    ? events.filter((e) => e.event_month === `2025-${selectedMonth}`)
    : events;

  const classificationCounts: Record<string, { count: number; impact: number }> = {};
  for (const e of events) {
    if (!classificationCounts[e.change_classification]) {
      classificationCounts[e.change_classification] = { count: 0, impact: 0 };
    }
    classificationCounts[e.change_classification].count += 1;
    classificationCounts[e.change_classification].impact += e.financial_impact?.total_impact || 0;
  }

  const janTotal = data.monthly_snapshots[0]?.total_attributed || 0;
  const annualizedChurn = data.monthly_snapshots.reduce((sum, s) => sum + s.lost_attributions, 0) / janTotal;

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total Attributed"
          value={formatNumber(data.current_attributed)}
          delta={data.net_change_ytd}
          deltaLabel="vs Jan"
          positive={data.net_change_ytd >= 0}
        />
        <MetricCard
          label="At Risk"
          value={formatNumber(data.current_at_risk)}
          subtext={formatCurrency(data.current_financial_exposure) + ' exposure'}
          alert
        />
        <MetricCard
          label="YTD Churn Rate"
          value={formatPercent(annualizedChurn)}
          subtext="vs ~12-15% industry benchmark"
        />
        <MetricCard
          label="Net Change"
          value={(data.net_change_ytd >= 0 ? '+' : '') + formatNumber(data.net_change_ytd)}
          subtext={formatPercent(data.net_change_pct_ytd) + ' YTD'}
          positive={data.net_change_ytd >= 0}
        />
      </div>

      {/* Hero chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Attribution Timeline — Performance Year 2025</h3>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData} onClick={(d) => {
            if (d?.activeLabel) setSelectedMonth(d.activeLabel);
          }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="label" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="total" domain={['dataMin - 20', 'dataMax + 20']} tick={{ fontSize: 12 }} />
            <YAxis yAxisId="change" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'total') return [formatNumber(value), 'Total Attributed'];
                if (name === 'new') return [formatNumber(value), 'New'];
                if (name === 'lost') return [formatNumber(Math.abs(value)), 'Lost'];
                if (name === 'net') return [formatNumber(value), 'Net Change'];
                return [value, name];
              }}
            />
            <Legend />
            <Area yAxisId="total" type="monotone" dataKey="total" fill="#e0f2fe" stroke="#0284c7" strokeWidth={2} name="total" />
            <Bar yAxisId="change" dataKey="new" fill="#22c55e" opacity={0.7} name="new" />
            <Bar yAxisId="change" dataKey="lost" fill="#ef4444" opacity={0.7} name="lost" />
            <Line yAxisId="change" type="monotone" dataKey="net" stroke="#6366f1" strokeWidth={2} dot={false} name="net" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Change event classification */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-900">Changes by Classification</h3>
          <div className="space-y-3">
            {Object.entries(classificationCounts)
              .sort((a, b) => b[1].count - a[1].count)
              .map(([cls, info]) => (
                <div key={cls} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={classNames(
                      'inline-block h-2.5 w-2.5 rounded-full',
                      cls === 'competing_provider' ? 'bg-red-500'
                        : cls === 'enrollment_gap' ? 'bg-amber-500'
                        : cls === 'new_enrollment' || cls === 'new_plurality' ? 'bg-green-500'
                        : 'bg-gray-400',
                    )} />
                    <span className="text-sm text-gray-700">{cls.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium tabular-nums text-gray-900">{info.count}</span>
                    <span className="text-xs tabular-nums text-gray-500 w-24 text-right">
                      {formatCurrency(info.impact)}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Quarterly summary */}
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-900">Quarterly Summary</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {['Q1', 'Q2', 'Q3', 'Q4'].map((q) => {
              const qd = (data.churn_by_quarter as Record<string, { new: number; lost: number; net: number }>)[q] || { new: 0, lost: 0, net: 0 };
              return (
                <div key={q} className="rounded-lg border border-gray-100 bg-gray-50 p-3">
                  <div className="text-xs font-semibold text-gray-500">{q}</div>
                  <div className="mt-1 text-xs text-green-600">+{qd.new} new</div>
                  <div className="text-xs text-red-600">-{qd.lost} lost</div>
                  <div className={classNames(
                    'mt-1 text-sm font-semibold tabular-nums',
                    qd.net >= 0 ? 'text-green-700' : 'text-red-700',
                  )}>
                    {qd.net >= 0 ? '+' : ''}{qd.net} net
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent events table */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">
            Change Events {selectedMonth ? `— ${new Date('2025-' + selectedMonth + '-01').toLocaleDateString('en-US', { month: 'long' })}` : ''}
          </h3>
          {selectedMonth && (
            <button onClick={() => setSelectedMonth(null)} className="text-xs text-slate-600 hover:underline">
              Show all
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500">
                <th className="pb-2 pr-4">Month</th>
                <th className="pb-2 pr-4">Member</th>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Classification</th>
                <th className="pb-2 pr-4">Provider</th>
                <th className="pb-2 pr-4 text-right">Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredEvents.slice(0, 20).map((e) => (
                <tr key={e.event_id} className="hover:bg-gray-50">
                  <td className="py-2 pr-4 tabular-nums text-gray-600">{e.event_month}</td>
                  <td className="py-2 pr-4 font-mono text-xs text-gray-900">{e.member_id}</td>
                  <td className="py-2 pr-4">
                    <span className={classNames(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                      e.event_type === 'lost_attribution' ? 'bg-red-50 text-red-700'
                        : e.event_type === 'new_attribution' ? 'bg-green-50 text-green-700'
                        : 'bg-gray-50 text-gray-700',
                    )}>
                      {e.event_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-gray-600">{e.change_classification.replace(/_/g, ' ')}</td>
                  <td className="py-2 pr-4 text-gray-600 text-xs">
                    {e.prior_provider?.name || e.new_provider?.name || '—'}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums font-medium text-gray-900">
                    {formatCurrency(e.financial_impact?.total_impact || 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredEvents.length > 20 && (
          <p className="mt-2 text-xs text-gray-400">Showing 20 of {filteredEvents.length} events</p>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label, value, delta, deltaLabel, subtext, positive, alert,
}: {
  label: string;
  value: string;
  delta?: number;
  deltaLabel?: string;
  subtext?: string;
  positive?: boolean;
  alert?: boolean;
}) {
  return (
    <div className={classNames(
      'rounded-xl border p-5',
      alert ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-white',
    )}>
      <div className="text-xs font-medium text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-gray-900">{value}</div>
      {delta !== undefined && (
        <div className={classNames(
          'mt-1 text-xs font-medium tabular-nums',
          positive ? 'text-green-600' : 'text-red-600',
        )}>
          {positive ? '↑' : '↓'} {Math.abs(delta)} {deltaLabel}
        </div>
      )}
      {subtext && <div className="mt-1 text-xs text-gray-500">{subtext}</div>}
    </div>
  );
}
