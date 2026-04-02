import { useEffect, useState } from 'react';
import { getClinicalBrief, submitClinicalFeedback } from '@/api/client';
import { classNames, formatCurrency } from '@/utils/formatters';
import FeedbackModal from './FeedbackModal';
import type {
  PatientBriefResponse,
  PriorityActionInfo,
  QualityGapInfo,
  CostContextInfo,
} from '@/types';

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  stable: { bg: 'bg-green-50', text: 'text-green-700', label: 'Stable' },
  moderate_risk: { bg: 'bg-yellow-50', text: 'text-yellow-700', label: 'At Risk' },
  high_risk: { bg: 'bg-red-50', text: 'text-red-700', label: 'High Risk' },
  new_attribution: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'New to Panel' },
};

const STATUS_DOT: Record<string, string> = {
  stable: 'bg-green-400',
  moderate_risk: 'bg-yellow-400',
  high_risk: 'bg-red-400',
  new_attribution: 'bg-blue-400',
};

interface Props {
  appointmentId: string;
  onBack: () => void;
  onDrilldown: (itemType: string, itemId: string) => void;
}

export default function PatientBrief({ appointmentId, onBack, onDrilldown }: Props) {
  const [brief, setBrief] = useState<PatientBriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackTarget, setFeedbackTarget] = useState<{ type: string; id: string } | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await getClinicalBrief(appointmentId);
        setBrief(data as unknown as PatientBriefResponse);
      } catch {
        setBrief(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [appointmentId]);

  async function handleFeedbackSubmit(feedback: string, note: string) {
    if (!feedbackTarget) return;
    await submitClinicalFeedback(appointmentId, {
      item_type: feedbackTarget.type,
      item_id: feedbackTarget.id,
      feedback,
      note,
    });
    setFeedbackOpen(false);
    const data = await getClinicalBrief(appointmentId);
    setBrief(data as unknown as PatientBriefResponse);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading brief...</span>
      </div>
    );
  }

  if (!brief) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-red-600">Brief not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">
          Back to schedule
        </button>
      </div>
    );
  }

  const attrStyle = STATUS_STYLES[brief.attribution_risk.status] || STATUS_STYLES.stable;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to schedule
      </button>

      {/* Header Bar */}
      <div className={classNames('rounded-xl p-4', attrStyle.bg)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-900">{brief.member_id}</span>
            <span className="text-xs text-gray-500">
              {brief.appointment_date} at {brief.appointment_time}
            </span>
            <span className="text-xs text-gray-500">{brief.provider_name}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className={classNames('h-2.5 w-2.5 rounded-full', STATUS_DOT[brief.attribution_risk.status] || 'bg-gray-400')} />
              <span className={classNames('text-xs font-medium', attrStyle.text)}>{attrStyle.label}</span>
            </div>
            <span className="rounded-full bg-white/80 px-2.5 py-1 text-xs font-medium text-gray-700">
              {brief.days_remaining_in_period} days remaining
            </span>
          </div>
        </div>
      </div>

      {/* Priority Actions */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Priority Actions</h3>
        {brief.priority_actions.length === 0 ? (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-center">
            <p className="text-sm text-gray-500">No priority actions for this encounter. Routine visit.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {brief.priority_actions.map((action: PriorityActionInfo) => (
              <button
                key={action.rank}
                onClick={() => onDrilldown('priority_action', String(action.rank))}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-4 hover:border-teal-300 hover:bg-teal-50/30 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center h-7 w-7 rounded-full bg-teal-100 text-teal-700 text-sm font-bold">
                    {action.rank}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{action.action_text}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{action.reason_text}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
                        {action.category.replace(/_/g, ' ')}
                      </span>
                      {action.closable_this_visit && (
                        <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">
                          Can close today
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Quality Gaps */}
      {brief.quality_gaps.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Care Actions Due
            <span className="ml-2 text-xs font-normal text-gray-400">
              {brief.closable_this_visit_count} of {brief.total_gap_count} can be closed today
            </span>
          </h3>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Measure</th>
                  <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase">Action Needed</th>
                  <th className="px-3 py-2 text-center text-[10px] font-semibold text-gray-500 uppercase">Today?</th>
                  <th className="px-3 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {brief.quality_gaps.map((gap: QualityGapInfo) => (
                  <tr
                    key={gap.measure_id}
                    onClick={() => onDrilldown('gap', gap.measure_id)}
                    className="hover:bg-teal-50/30 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-2 text-xs text-gray-900">{gap.measure_name}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{gap.action_needed}</td>
                    <td className="px-3 py-2 text-center">
                      {gap.closable_this_visit ? (
                        <svg className="h-4 w-4 text-green-500 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="h-4 w-4 text-gray-300 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className={classNames(
                        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                        gap.priority_score > 0.6 ? 'bg-red-100 text-red-700' :
                        gap.priority_score > 0.4 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600',
                      )}>
                        {gap.priority_score > 0.6 ? 'High' : gap.priority_score > 0.4 ? 'Medium' : 'Low'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {brief.is_feedback_patient && (
            <button
              onClick={() => {
                const gap = brief.quality_gaps[0];
                if (gap) {
                  setFeedbackTarget({ type: 'gap', id: gap.measure_id });
                  setFeedbackOpen(true);
                }
              }}
              className="mt-2 text-xs text-teal-600 hover:text-teal-700 font-medium"
            >
              Mark a recommendation as addressed or declined
            </button>
          )}
        </section>
      )}

      {/* HCC Opportunities */}
      {brief.hcc_opportunities.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Conditions to Document</h3>
          <div className="space-y-2">
            {brief.hcc_opportunities.map((hcc) => (
              <button
                key={hcc.hcc_category}
                onClick={() => onDrilldown('hcc', hcc.hcc_category)}
                className="w-full text-left rounded-lg border border-gray-200 bg-white p-3 hover:border-teal-300 transition-colors"
              >
                <p className="text-sm text-gray-900">{hcc.condition_name}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  <span className="font-mono">{hcc.icd10_code}</span> — Document if clinically appropriate
                </p>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Cost Context */}
      <section>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Cost Context</h3>
        <div
          onClick={() => onDrilldown('cost', 'cost_context')}
          className="rounded-lg border border-gray-200 bg-white p-4 cursor-pointer hover:border-teal-300 transition-colors"
        >
          <CostGauge context={brief.cost_context} />
        </div>
      </section>

      {/* Attribution Note */}
      {brief.attribution_risk.status !== 'stable' && (
        <div className={classNames(
          'rounded-lg p-4',
          brief.attribution_risk.status === 'new_attribution' ? 'bg-blue-50 border border-blue-200' :
          brief.attribution_risk.status === 'moderate_risk' ? 'bg-yellow-50 border border-yellow-200' :
          'bg-red-50 border border-red-200',
        )}>
          <div className="flex items-start gap-2">
            <svg className="h-4 w-4 text-current flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <div>
              {brief.attribution_risk.risk_factors.map((f, i) => (
                <p key={i} className="text-xs text-gray-700">{f}</p>
              ))}
              {brief.attribution_risk.recommended_action && (
                <p className="text-xs font-medium text-gray-900 mt-1">
                  {brief.attribution_risk.recommended_action}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Crossover Banner */}
      {brief.is_crossover_patient && brief.crossover_discrepancy && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <div className="flex items-center gap-2 mb-1">
            <svg className="h-4 w-4 text-purple-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            <span className="text-xs font-semibold text-purple-700">Settlement Reconciliation Connection</span>
          </div>
          <p className="text-xs text-purple-600">
            {(brief.crossover_discrepancy as Record<string, unknown>).description as string}
          </p>
        </div>
      )}

      {/* Feedback Modal */}
      <FeedbackModal
        isOpen={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        onSubmit={handleFeedbackSubmit}
      />
    </div>
  );
}

function CostGauge({ context }: { context: CostContextInfo }) {
  const pct = Math.min(200, Math.max(0, context.cost_ratio * 100));
  const barWidth = Math.min(100, pct / 2);

  return (
    <div>
      <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
        <span>Below Expected</span>
        <span>At Expected</span>
        <span>Above Expected</span>
      </div>
      <div className="relative h-3 rounded-full bg-gray-100 overflow-hidden">
        <div className="absolute inset-y-0 left-1/2 w-px bg-gray-300" />
        <div
          className={classNames(
            'absolute inset-y-0 left-0 rounded-full transition-all',
            context.cost_status === 'below_expected' ? 'bg-green-400' :
            context.cost_status === 'at_expected' ? 'bg-gray-400' : 'bg-red-400',
          )}
          style={{ width: `${barWidth}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-600">YTD: {formatCurrency(context.ytd_cost)}</span>
        {context.top_cost_driver && (
          <span className="text-xs text-red-600">Driver: {context.top_cost_driver}</span>
        )}
      </div>
    </div>
  );
}
