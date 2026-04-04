import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, BarChart, Bar, CartesianGrid } from 'recharts';
import { formatCurrency, formatNumber, classNames } from '@/utils/formatters';
import { getSurveillanceProviders, getSurveillanceProviderDetail } from '@/api/client';

interface ProviderPanel {
  provider_npi: string;
  provider_name: string;
  specialty: string;
  current_panel_size: number;
  jan_panel_size: number;
  net_change: number;
  net_change_pct: number;
  churn_rate_annualized: number;
  members_at_risk: number;
  financial_exposure: number;
  monthly_trend: number[];
  cascade_flag: boolean;
}

interface ProviderDetail {
  provider: ProviderPanel;
  change_events: Array<Record<string, unknown>>;
  at_risk_members: Array<Record<string, unknown>>;
}

export default function ProviderPanels({
  selectedNpi,
  onSelectProvider,
}: {
  selectedNpi: string | null;
  onSelectProvider: (npi: string) => void;
}) {
  const [providers, setProviders] = useState<ProviderPanel[]>([]);
  const [detail, setDetail] = useState<ProviderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = (await getSurveillanceProviders()) as unknown as ProviderPanel[];
        setProviders(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedNpi) { setDetail(null); return; }
    async function loadDetail() {
      try {
        const d = (await getSurveillanceProviderDetail(selectedNpi!)) as unknown as ProviderDetail;
        setDetail(d);
      } catch { /* ignore */ }
    }
    loadDetail();
  }, [selectedNpi]);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading providers...</div>;
  if (error) return <div className="py-12 text-center text-red-600">{error}</div>;

  if (detail) {
    return <ProviderDetailView detail={detail} onBack={() => { onSelectProvider(''); setDetail(null); }} />;
  }

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">Provider panels sorted by financial exposure (highest first).</p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {providers.map((p) => {
          const trendData = p.monthly_trend.map((val, i) => ({ month: months[i], size: val }));
          return (
            <button
              key={p.provider_npi}
              onClick={() => onSelectProvider(p.provider_npi)}
              className="rounded-xl border border-gray-200 bg-white p-5 text-left transition hover:shadow-md hover:border-gray-300"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-900">{p.provider_name || p.provider_npi}</div>
                  <div className="text-xs text-gray-500">{p.specialty}</div>
                </div>
                {p.cascade_flag && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                    CASCADE
                  </span>
                )}
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-2xl font-semibold tabular-nums text-gray-900">{p.current_panel_size}</span>
                <span className={classNames(
                  'text-xs font-medium tabular-nums',
                  p.net_change >= 0 ? 'text-green-600' : 'text-red-600',
                )}>
                  {p.net_change >= 0 ? '↑' : '↓'}{Math.abs(p.net_change)} vs Jan
                </span>
              </div>
              <div className="mt-2 h-12">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <Line type="monotone" dataKey="size" stroke="#475569" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                <span>{p.members_at_risk} at risk</span>
                <span className="tabular-nums">{formatCurrency(p.financial_exposure)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ProviderDetailView({ detail, onBack }: { detail: ProviderDetail; onBack: () => void }) {
  const p = detail.provider;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const trendData = p.monthly_trend.map((val, i) => ({ month: months[i], size: val }));

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="text-sm text-slate-600 hover:underline">
        ← Back to Provider Panels
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{p.provider_name || p.provider_npi}</h2>
          <div className="text-sm text-gray-500">{p.specialty} — NPI: {p.provider_npi}</div>
        </div>
        {p.cascade_flag && (
          <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
            CASCADE ALERT
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Current Panel" value={formatNumber(p.current_panel_size)} />
        <StatCard label="Jan Panel" value={formatNumber(p.jan_panel_size)} />
        <StatCard label="Net Change" value={(p.net_change >= 0 ? '+' : '') + p.net_change} positive={p.net_change >= 0} />
        <StatCard label="At Risk" value={formatNumber(p.members_at_risk)} alert />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Panel Size Trend</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis domain={['dataMin - 5', 'dataMax + 5']} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="size" fill="#475569" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Change events for this provider */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">Change Events ({detail.change_events.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500">
                <th className="pb-2 pr-4">Month</th>
                <th className="pb-2 pr-4">Member</th>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Classification</th>
                <th className="pb-2 pr-4">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {detail.change_events.slice(0, 30).map((e: Record<string, unknown>, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="py-2 pr-4 tabular-nums text-gray-600">{String(e.event_month)}</td>
                  <td className="py-2 pr-4 font-mono text-xs">{String(e.member_id)}</td>
                  <td className="py-2 pr-4">
                    <span className={classNames(
                      'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                      e.event_type === 'lost_attribution' ? 'bg-red-50 text-red-700'
                        : e.event_type === 'new_attribution' ? 'bg-green-50 text-green-700'
                        : 'bg-gray-50 text-gray-700',
                    )}>
                      {String(e.event_type).replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-xs text-gray-600">{String(e.change_classification).replace(/_/g, ' ')}</td>
                  <td className="py-2 pr-4 text-xs text-gray-500 max-w-xs truncate">{String(e.reason || '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* At-risk members */}
      {detail.at_risk_members.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6">
          <h3 className="mb-3 text-sm font-semibold text-amber-900">
            At-Risk Members ({detail.at_risk_members.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-amber-200 text-left text-xs font-medium text-amber-700">
                  <th className="pb-2 pr-4">Member</th>
                  <th className="pb-2 pr-4">Urgency</th>
                  <th className="pb-2 pr-4">Action</th>
                  <th className="pb-2 pr-4 text-right">ROI</th>
                  <th className="pb-2 pr-4 text-right">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {detail.at_risk_members.map((m: Record<string, unknown>, i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 font-mono text-xs">{String(m.member_id)}</td>
                    <td className="py-2 pr-4">
                      <UrgencyBadge urgency={String(m.urgency)} />
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-700 max-w-xs truncate">{String(m.recommended_action || '')}</td>
                    <td className="py-2 pr-4 text-right tabular-nums font-medium">{Number(m.roi_estimate).toFixed(1)}x</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{formatCurrency(Number((m.financial_impact_if_lost as Record<string, number>)?.total || 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, positive, alert }: { label: string; value: string; positive?: boolean; alert?: boolean }) {
  return (
    <div className={classNames('rounded-lg border p-3', alert ? 'border-amber-200 bg-amber-50' : 'border-gray-100 bg-gray-50')}>
      <div className="text-xs text-gray-500">{label}</div>
      <div className={classNames(
        'mt-0.5 text-lg font-semibold tabular-nums',
        positive === true ? 'text-green-700' : positive === false ? 'text-red-700' : 'text-gray-900',
      )}>{value}</div>
    </div>
  );
}

function UrgencyBadge({ urgency }: { urgency: string }) {
  return (
    <span className={classNames(
      'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
      urgency === 'critical' ? 'bg-red-100 text-red-800'
        : urgency === 'high' ? 'bg-amber-100 text-amber-800'
        : 'bg-gray-100 text-gray-700',
    )}>
      {urgency}
    </span>
  );
}
