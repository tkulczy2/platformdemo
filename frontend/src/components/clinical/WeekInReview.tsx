import { useEffect, useState } from 'react';
import { getClinicalWeekSummary } from '@/api/client';
import { formatCurrency, formatNumber } from '@/utils/formatters';
import type { WeekSummary } from '@/types';

interface Props {
  onBack: () => void;
}

export default function WeekInReview({ onBack }: Props) {
  const [summary, setSummary] = useState<WeekSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await getClinicalWeekSummary();
        setSummary(data as unknown as WeekSummary);
      } catch {
        setSummary(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading week summary...</span>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-gray-500">Week summary not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">Back</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mb-2"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            Back to schedule
          </button>
          <h2 className="text-lg font-semibold text-gray-900">Week in Review</h2>
        </div>
      </div>

      {/* Key Numbers */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Total Encounters', value: formatNumber(summary.total_encounters) },
          { label: 'Patients with Gaps', value: formatNumber(summary.patients_with_gaps) },
          { label: 'Gaps Addressable', value: formatNumber(summary.total_gaps_addressable) },
          { label: 'Closable This Week', value: formatNumber(summary.closable_this_week) },
          { label: 'At-Risk Patients', value: formatNumber(summary.at_risk_patients) },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-[10px] text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Quality Gap Breakdown */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Quality Measure Gaps This Week</h3>
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Measure</th>
                <th className="px-4 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Gaps Found</th>
                <th className="px-4 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Closable</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {Object.entries(summary.measure_gaps).map(([id, info]) => (
                <tr key={id}>
                  <td className="px-4 py-2 text-xs text-gray-900">{info.measure_name}</td>
                  <td className="px-4 py-2 text-xs text-gray-700 text-right">{info.gap_count}</td>
                  <td className="px-4 py-2 text-xs text-green-700 text-right">{info.closable_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Cost Summary */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Cost Summary</h3>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatCurrency(summary.cost_summary.average_ytd_cost)}
            </p>
            <p className="text-[10px] text-gray-500">Avg YTD Cost</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatNumber(summary.cost_summary.high_cost_patients)}
            </p>
            <p className="text-[10px] text-gray-500">High-Cost Patients</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
            <p className="text-lg font-bold text-gray-900">
              {formatCurrency(summary.cost_summary.benchmark_pmpm)}
            </p>
            <p className="text-[10px] text-gray-500">Benchmark PMPM</p>
          </div>
        </div>
      </section>

      {/* Crossover Section */}
      {summary.crossover.exists && (
        <section className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <h3 className="text-sm font-semibold text-purple-800 mb-2">Settlement Reconciliation Connection</h3>
          <p className="text-xs text-purple-600">
            Patient {summary.crossover.member_id} seen this week has an open care action AND a discrepancy
            in the Settlement Reconciliation view. One engine, two audiences, one source of truth.
          </p>
        </section>
      )}

      {/* Feedback Section */}
      {summary.feedback.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Provider Feedback</h3>
          {summary.feedback.map((fb, i) => (
            <div key={i} className="rounded-lg border border-teal-200 bg-teal-50 p-3 text-xs text-teal-700">
              Feedback on {fb.item_type}/{fb.item_id}: <strong>{fb.feedback}</strong>
              {fb.note && <span className="text-teal-500"> — {fb.note}</span>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
