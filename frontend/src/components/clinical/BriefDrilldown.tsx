import { useEffect, useState } from 'react';
import { getClinicalBriefDrilldown, getSourceCode } from '@/api/client';

interface Props {
  appointmentId: string;
  itemType: string;
  itemId: string;
  onBack: () => void;
}

export default function BriefDrilldown({ appointmentId, itemType, itemId, onBack }: Props) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [sourceCode, setSourceCode] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const dd = await getClinicalBriefDrilldown(appointmentId, itemType, itemId);
        setData(dd as unknown as Record<string, unknown>);

        const prov = dd.provenance as Record<string, unknown>;
        if (prov?.step) {
          try {
            const stepName = prov.step as string;
            const module = `step_${prov.step_number}_${stepName}`;
            const func = stepName === 'quality' ? 'calculate_quality_measures' :
                         stepName === 'attribution' ? 'assign_attribution' :
                         stepName === 'cost' ? 'calculate_cost' : '';
            if (func) {
              const code = await getSourceCode(module, func);
              setSourceCode(code.source || '');
            }
          } catch { /* Code loading is optional */ }
        }
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [appointmentId, itemType, itemId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <span className="text-sm text-gray-500">Loading provenance...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-gray-500">Drilldown data not available</p>
        <button onClick={onBack} className="mt-2 text-xs text-brand-600 hover:underline">Back</button>
      </div>
    );
  }

  const detail = data.detail as Record<string, unknown>;
  const question = data.clinical_question as string;

  return (
    <div className="space-y-4">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
      >
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
        </svg>
        Back to brief
      </button>

      {/* Clinical question header */}
      <div className="rounded-lg bg-teal-50 border border-teal-200 px-4 py-3">
        <p className="text-sm font-medium text-teal-800">{question}</p>
      </div>

      {/* Three-panel layout */}
      <div className="grid grid-cols-3 gap-4 min-h-[50vh]">
        {/* Contract Language */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Contract Language</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto">
            <p className="text-xs text-gray-700 leading-relaxed">
              {data.provenance
                ? JSON.stringify(data.provenance as Record<string, unknown>, null, 2)
                : 'Contract clause reference available in full Platform view.'}
            </p>
          </div>
        </div>

        {/* Interpretation + Data */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Interpretation & Data</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto space-y-3">
            {Object.entries(detail).map(([key, value]) => {
              if (key === 'provenance') return null;
              return (
                <div key={key}>
                  <p className="text-[10px] font-semibold text-gray-400 uppercase">{key.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-gray-700 mt-0.5">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Code */}
        <div className="rounded-lg border border-gray-200 bg-white overflow-hidden flex flex-col">
          <div className="border-b border-gray-100 bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-semibold text-gray-500 uppercase">Code</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto">
            {sourceCode ? (
              <pre className="text-[11px] text-gray-700 font-mono whitespace-pre-wrap leading-relaxed">
                {sourceCode}
              </pre>
            ) : (
              <p className="text-xs text-gray-400 italic">
                Source code available when running with live API.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
