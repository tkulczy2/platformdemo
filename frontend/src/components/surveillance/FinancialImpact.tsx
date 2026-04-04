import { useState, useEffect } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, formatNumber, classNames } from '@/utils/formatters';
import { getSurveillanceFinancialImpact, getSurveillanceQualityImpact } from '@/api/client';

interface FinancialData {
  by_classification: Record<string, { count: number; financial_impact: number }>;
  by_quarter: Record<string, { new: number; lost: number; net: number }>;
  cumulative_monthly: Array<{ month: string; cumulative_impact: number }>;
  total_at_risk: number;
  total_intervention_cost: number;
  total_potential_recovery: number;
  aggregate_roi: number;
}

interface QualityMeasure {
  measure_name: string;
  current_rate: number;
  rate_if_at_risk_lost: number;
  rate_change: number;
  members_at_stake: number;
  eligible_count: number;
}

export default function FinancialImpact() {
  const [financial, setFinancial] = useState<FinancialData | null>(null);
  const [quality, setQuality] = useState<Record<string, QualityMeasure> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const [fin, qual] = await Promise.all([
          getSurveillanceFinancialImpact() as unknown as Promise<FinancialData>,
          getSurveillanceQualityImpact() as unknown as Promise<Record<string, QualityMeasure>>,
        ]);
        setFinancial(fin);
        setQuality(qual);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="py-12 text-center text-gray-500">Loading financial data...</div>;
  if (error) return <div className="py-12 text-center text-red-600">{error}</div>;
  if (!financial) return null;

  const cumulativeData = financial.cumulative_monthly.map((m) => ({
    month: new Date(m.month + '-01').toLocaleDateString('en-US', { month: 'short' }),
    impact: m.cumulative_impact,
  }));

  const classificationData = Object.entries(financial.by_classification)
    .map(([cls, info]) => ({ name: cls.replace(/_/g, ' '), ...info }))
    .sort((a, b) => b.financial_impact - a.financial_impact);

  return (
    <div className="space-y-6">
      {/* Intervention ROI summary */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Intervention ROI Summary</h3>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div className="rounded-lg border border-red-100 bg-red-50 p-4 text-center">
            <div className="text-xs font-medium text-red-600">Total Financial Exposure</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-red-800">
              {formatCurrency(financial.total_at_risk)}
            </div>
            <div className="mt-1 text-xs text-red-500">from at-risk members</div>
          </div>
          <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 text-center">
            <div className="text-xs font-medium text-gray-600">Total Intervention Cost</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-gray-900">
              {formatCurrency(financial.total_intervention_cost)}
            </div>
            <div className="mt-1 text-xs text-gray-500">for all retention actions</div>
          </div>
          <div className="rounded-lg border border-green-100 bg-green-50 p-4 text-center">
            <div className="text-xs font-medium text-green-600">Expected Recovery</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-green-800">
              {formatCurrency(financial.total_potential_recovery)}
            </div>
            <div className="mt-1 text-xs text-green-500">{financial.aggregate_roi.toFixed(1)}x return on investment</div>
          </div>
        </div>
      </div>

      {/* Cumulative impact chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Cumulative Financial Impact Over Time</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={cumulativeData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(value: number) => [formatCurrency(value), 'Cumulative Impact']} />
            <Area type="monotone" dataKey="impact" fill="#fecdd3" stroke="#e11d48" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Impact by classification */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h3 className="mb-4 text-sm font-semibold text-gray-900">Impact by Classification</h3>
        <ResponsiveContainer width="100%" height={Math.max(200, classificationData.length * 40)}>
          <BarChart data={classificationData} layout="vertical" margin={{ left: 140 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={130} />
            <Tooltip formatter={(value: number, name: string) => {
              if (name === 'financial_impact') return [formatCurrency(value), 'Financial Impact'];
              return [formatNumber(value), 'Count'];
            }} />
            <Bar dataKey="financial_impact" fill="#475569" radius={[0, 4, 4, 0]} name="financial_impact" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Quality impact table */}
      {quality && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-900">Quality Measure Impact</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500">
                  <th className="pb-2 pr-4">Measure</th>
                  <th className="pb-2 pr-4 text-right">Current Rate</th>
                  <th className="pb-2 pr-4 text-right">Rate if Lost</th>
                  <th className="pb-2 pr-4 text-right">Change</th>
                  <th className="pb-2 pr-4 text-right">Members at Stake</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {Object.entries(quality).map(([key, m]) => (
                  <tr key={key} className="hover:bg-gray-50">
                    <td className="py-3 pr-4 text-gray-900">{m.measure_name || key.replace(/_/g, ' ')}</td>
                    <td className="py-3 pr-4 text-right tabular-nums font-medium">{m.current_rate.toFixed(1)}%</td>
                    <td className="py-3 pr-4 text-right tabular-nums">{m.rate_if_at_risk_lost.toFixed(1)}%</td>
                    <td className={classNames(
                      'py-3 pr-4 text-right tabular-nums font-medium',
                      m.rate_change < 0 ? 'text-red-600' : m.rate_change > 0 ? 'text-green-600' : 'text-gray-400',
                    )}>
                      {m.rate_change >= 0 ? '+' : ''}{m.rate_change.toFixed(1)}%
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">{m.members_at_stake}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {Object.values(quality).some((m) => m.rate_change < -5) && (
            <p className="mt-3 text-xs text-red-600">
              Warning: Attribution losses may push quality scores below the contract quality gate threshold.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
