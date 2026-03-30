import { classNames } from '@/utils/formatters';

interface DataReference {
  file: string;
  row_index: number;
  columns: Record<string, string | number | boolean | null>;
  description?: string;
}

interface MemberDetailData {
  member_id: string;
  outcome: string;
  outcome_value: string | number | boolean | null;
  data_references: DataReference[];
  logic_trace: string[];
  flags: string[];
}

interface IntermediateValue {
  label: string;
  value: string | number | boolean | null;
}

interface LogicPanelProps {
  logicSummary: string;
  memberDetail: MemberDetailData | null;
  intermediateValues?: IntermediateValue[];
  stepName?: string;
}

/**
 * Center panel of the three-panel drill-down view.
 * Shows the plain-English interpretation, intermediate calculation values,
 * and the actual source data rows that drove the member's outcome.
 */
export default function LogicPanel({
  logicSummary,
  memberDetail,
  intermediateValues,
  stepName,
}: LogicPanelProps) {
  // Group data references by source file
  const refsByFile: Record<string, DataReference[]> = {};
  if (memberDetail) {
    for (const ref of memberDetail.data_references) {
      const key = ref.file || 'unknown';
      if (!refsByFile[key]) refsByFile[key] = [];
      refsByFile[key].push(ref);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-brand-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
          <h3 className="text-sm font-semibold text-gray-900">Logic &amp; Data</h3>
          {stepName && (
            <span className="text-xs text-gray-500">-- {stepName}</span>
          )}
        </div>
        <p className="mt-1 text-xs text-gray-500">
          How the contract was interpreted and which data rows drove the result
        </p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* ---------------------------------------------------------------- */}
        {/* Member outcome banner                                             */}
        {/* ---------------------------------------------------------------- */}
        {memberDetail && (
          <div className={classNames(
            'mx-4 mt-4 rounded-lg border px-4 py-3',
            memberDetail.outcome.toLowerCase().includes('excluded')
              ? 'border-red-200 bg-red-50'
              : 'border-green-200 bg-green-50',
          )}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Member {memberDetail.member_id}
                </p>
                <p className={classNames(
                  'text-sm font-semibold mt-0.5',
                  memberDetail.outcome.toLowerCase().includes('excluded')
                    ? 'text-red-800'
                    : 'text-green-800',
                )}>
                  {memberDetail.outcome}
                </p>
              </div>
              {memberDetail.outcome_value != null && (
                <span className={classNames(
                  'text-lg font-bold',
                  memberDetail.outcome.toLowerCase().includes('excluded')
                    ? 'text-red-700'
                    : 'text-green-700',
                )}>
                  {String(memberDetail.outcome_value)}
                </span>
              )}
            </div>
            {/* Flags */}
            {memberDetail.flags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {memberDetail.flags.map((flag, i) => (
                  <span key={i} className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Logic summary                                                     */}
        {/* ---------------------------------------------------------------- */}
        <div className="px-4 pt-4 pb-2">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Logic Explanation
          </h4>
          <p className="text-sm leading-relaxed text-gray-700 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2.5">
            {logicSummary}
          </p>
        </div>

        {/* ---------------------------------------------------------------- */}
        {/* Logic trace (member-specific reasoning steps)                     */}
        {/* ---------------------------------------------------------------- */}
        {memberDetail && memberDetail.logic_trace.length > 0 && (
          <div className="px-4 pt-3 pb-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Reasoning Steps
            </h4>
            <ol className="space-y-1.5">
              {memberDetail.logic_trace.map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="flex-shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-[10px] font-bold text-gray-500 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="leading-snug">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Intermediate values                                               */}
        {/* ---------------------------------------------------------------- */}
        {intermediateValues && intermediateValues.length > 0 && (
          <div className="px-4 pt-3 pb-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Intermediate Values
            </h4>
            <div className="rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <tbody>
                  {intermediateValues.map((iv, i) => (
                    <tr
                      key={i}
                      className={classNames(
                        'border-b border-gray-100 last:border-0',
                        i % 2 === 0 ? 'bg-white' : 'bg-gray-50',
                      )}
                    >
                      <td className="px-3 py-1.5 text-gray-500 font-medium whitespace-nowrap">
                        {iv.label}
                      </td>
                      <td className="px-3 py-1.5 text-gray-900 font-mono text-right">
                        {iv.value != null ? String(iv.value) : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* Source data tables                                                 */}
        {/* ---------------------------------------------------------------- */}
        {Object.keys(refsByFile).length > 0 && (
          <div className="px-4 pt-3 pb-4">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Source Data
            </h4>
            <div className="space-y-3">
              {Object.entries(refsByFile).map(([fileName, refs]) => {
                // Collect all column keys across references
                const allColumns = new Set<string>();
                refs.forEach((r) => Object.keys(r.columns).forEach((c) => allColumns.add(c)));
                const cols = Array.from(allColumns);

                return (
                  <div key={fileName} className="rounded-lg border border-gray-200 overflow-hidden">
                    {/* File name subtitle */}
                    <div className="bg-gray-50 px-3 py-1.5 border-b border-gray-200 flex items-center gap-2">
                      <svg className="h-3.5 w-3.5 text-gray-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                      <span className="text-xs font-mono text-gray-600">{fileName}</span>
                      <span className="text-[10px] text-gray-400">
                        ({refs.length} row{refs.length !== 1 ? 's' : ''})
                      </span>
                    </div>

                    {/* Data table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="bg-gray-50/50">
                            <th className="px-2 py-1.5 text-left font-semibold text-gray-500 whitespace-nowrap">
                              Row
                            </th>
                            {cols.map((col) => (
                              <th
                                key={col}
                                className="px-2 py-1.5 text-left font-semibold text-gray-500 whitespace-nowrap"
                              >
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {refs.map((ref, ri) => (
                            <tr
                              key={ri}
                              className="border-t border-gray-100 bg-yellow-50/40 hover:bg-yellow-50"
                            >
                              <td className="px-2 py-1.5 font-mono text-gray-400 whitespace-nowrap">
                                #{ref.row_index}
                              </td>
                              {cols.map((col) => (
                                <td
                                  key={col}
                                  className="px-2 py-1.5 font-mono text-gray-800 whitespace-nowrap"
                                >
                                  {ref.columns[col] != null
                                    ? String(ref.columns[col])
                                    : '--'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty state when no member is selected */}
        {!memberDetail && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <svg className="h-10 w-10 mb-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
            <p className="text-sm">Select a member to see detailed logic and data</p>
          </div>
        )}
      </div>
    </div>
  );
}
