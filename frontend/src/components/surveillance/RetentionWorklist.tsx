import { useState, useEffect, useMemo } from 'react';
import { formatCurrency, classNames } from '@/utils/formatters';
import { getSurveillanceWorklist } from '@/api/client';
import { useNavigate } from 'react-router-dom';

interface WorklistItem {
  rank: number;
  member_id: string;
  attributed_provider: { npi: string; name: string };
  urgency: string;
  risk_factors: string[];
  financial_impact_if_lost: { tcoc: number; shared_savings: number; quality_bonus: number; total: number };
  quality_measures_at_stake: Array<{ measure_id: string; measure_name: string }>;
  recommended_action: string;
  roi_estimate: number;
  intervention_cost_estimate: number;
  recovery_probability: number;
  has_upcoming_appointment: boolean;
  next_appointment_date: string | null;
  competing_provider: { npi: string; visit_count: number } | null;
  visits_this_year: number;
  days_remaining_in_period: number;
}

interface WorklistResponse {
  total: number;
  summary: {
    total_financial_exposure: number;
    total_intervention_cost: number;
    total_potential_recovery: number;
    aggregate_roi: number;
  };
  items: WorklistItem[];
}

export default function RetentionWorklist() {
  const [data, setData] = useState<WorklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [urgencyFilter, setUrgencyFilter] = useState<string>('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string>('roi');
  const [sortAsc, setSortAsc] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const d = (await getSurveillanceWorklist()) as unknown as WorklistResponse;
        setData(d);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    let items = [...data.items];
    if (urgencyFilter) {
      items = items.filter((w) => w.urgency === urgencyFilter);
    }
    items.sort((a, b) => {
      let va: number, vb: number;
      switch (sortKey) {
        case 'roi': va = a.roi_estimate; vb = b.roi_estimate; break;
        case 'impact': va = a.financial_impact_if_lost.total; vb = b.financial_impact_if_lost.total; break;
        case 'quality': va = a.quality_measures_at_stake.length; vb = b.quality_measures_at_stake.length; break;
        default: va = a.roi_estimate; vb = b.roi_estimate;
      }
      return sortAsc ? va - vb : vb - va;
    });
    return items;
  }, [data, urgencyFilter, sortKey, sortAsc]);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading worklist...</div>;
  if (error) return <div className="py-12 text-center text-red-600">{error}</div>;
  if (!data) return null;

  const s = data.summary;

  function handleSort(key: string) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <div>
            <div className="text-xs text-gray-500">Worklist Items</div>
            <div className="text-lg font-semibold tabular-nums">{filtered.length}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Financial Exposure</div>
            <div className="text-lg font-semibold tabular-nums text-red-700">{formatCurrency(s.total_financial_exposure)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Intervention Cost</div>
            <div className="text-lg font-semibold tabular-nums">{formatCurrency(s.total_intervention_cost)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Potential Recovery</div>
            <div className="text-lg font-semibold tabular-nums text-green-700">{formatCurrency(s.total_potential_recovery)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Aggregate ROI</div>
            <div className="text-lg font-semibold tabular-nums">{s.aggregate_roi.toFixed(1)}x</div>
          </div>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          If every retention action on this list is executed, projected recovery is {formatCurrency(s.total_potential_recovery)} based on probability-weighted estimates.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium text-gray-500">Urgency:</span>
        {['', 'critical', 'high', 'moderate'].map((u) => (
          <button
            key={u}
            onClick={() => setUrgencyFilter(u)}
            className={classNames(
              'rounded-full px-3 py-1 text-xs font-medium transition',
              urgencyFilter === u
                ? 'bg-slate-700 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
            )}
          >
            {u || 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium text-gray-500">
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Member</th>
              <th className="px-4 py-3">Provider</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3 cursor-pointer hover:text-gray-900" onClick={() => handleSort('impact')}>
                Impact {sortKey === 'impact' ? (sortAsc ? '↑' : '↓') : ''}
              </th>
              <th className="px-4 py-3 cursor-pointer hover:text-gray-900" onClick={() => handleSort('quality')}>
                Quality {sortKey === 'quality' ? (sortAsc ? '↑' : '↓') : ''}
              </th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3 cursor-pointer hover:text-gray-900" onClick={() => handleSort('roi')}>
                ROI {sortKey === 'roi' ? (sortAsc ? '↑' : '↓') : ''}
              </th>
              <th className="px-4 py-3">Urgency</th>
              <th className="px-4 py-3">Next Appt</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((w, idx) => (
              <>
                <tr
                  key={w.member_id}
                  onClick={() => setExpandedRow(expandedRow === w.member_id ? null : w.member_id)}
                  className="cursor-pointer hover:bg-gray-50"
                >
                  <td className="px-4 py-3 tabular-nums text-gray-400">{idx + 1}</td>
                  <td className="px-4 py-3 font-mono text-xs font-medium text-gray-900">{w.member_id}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{w.attributed_provider.name || w.attributed_provider.npi}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {w.risk_factors.length > 0 ? w.risk_factors[0].slice(0, 30) + '...' : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-medium text-gray-900">
                    {formatCurrency(w.financial_impact_if_lost.total)}
                  </td>
                  <td className="px-4 py-3 text-center tabular-nums">
                    {w.quality_measures_at_stake.length > 0 ? (
                      <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                        {w.quality_measures_at_stake.length}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 max-w-[200px] truncate">{w.recommended_action}</td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold text-gray-900">{w.roi_estimate.toFixed(1)}x</td>
                  <td className="px-4 py-3"><UrgencyBadge urgency={w.urgency} /></td>
                  <td className="px-4 py-3 tabular-nums text-xs">
                    {w.has_upcoming_appointment ? (
                      <span className="text-green-600">{w.next_appointment_date || 'Yes'}</span>
                    ) : '—'}
                  </td>
                </tr>
                {expandedRow === w.member_id && (
                  <tr key={w.member_id + '-detail'}>
                    <td colSpan={10} className="bg-gray-50 px-6 py-4">
                      <ExpandedDetail item={w} onNavigateClinical={() => navigate('/clinical')} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExpandedDetail({ item, onNavigateClinical }: { item: WorklistItem; onNavigateClinical: () => void }) {
  const fi = item.financial_impact_if_lost;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <div className="text-xs text-gray-500">TCOC</div>
          <div className="text-sm font-medium tabular-nums">{formatCurrency(fi.tcoc)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Shared Savings</div>
          <div className="text-sm font-medium tabular-nums">{formatCurrency(fi.shared_savings)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Quality Bonus</div>
          <div className="text-sm font-medium tabular-nums">{formatCurrency(fi.quality_bonus)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500">Recovery Probability</div>
          <div className="text-sm font-medium tabular-nums">{(item.recovery_probability * 100).toFixed(0)}%</div>
        </div>
      </div>

      {item.risk_factors.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 mb-1">Risk Factors</div>
          <ul className="list-disc list-inside text-xs text-gray-700 space-y-0.5">
            {item.risk_factors.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}

      {item.competing_provider && (
        <div className="text-xs text-gray-600">
          Competing provider: NPI {item.competing_provider.npi} ({item.competing_provider.visit_count} visits)
        </div>
      )}

      {item.quality_measures_at_stake.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 mb-1">Quality Measures at Stake</div>
          <div className="flex flex-wrap gap-1">
            {item.quality_measures_at_stake.map((m) => (
              <span key={m.measure_id} className="rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-700">
                {m.measure_name || m.measure_id}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-2">
        {item.has_upcoming_appointment && (
          <button onClick={onNavigateClinical} className="text-xs font-medium text-slate-700 hover:underline">
            View Pre-Visit Brief →
          </button>
        )}
        <button onClick={() => { /* navigate to reconciliation */ }} className="text-xs font-medium text-slate-700 hover:underline">
          View in Settlement Reconciliation →
        </button>
      </div>
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
