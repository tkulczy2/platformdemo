import { classNames } from '@/utils/formatters';

interface ContractClause {
  id: string;
  text: string;
  section?: string;
  title?: string;
}

interface ParameterChange {
  name: string;
  defaultValue: string | number | boolean;
  currentValue: string | number | boolean;
}

interface ContractPanelProps {
  clauses: ContractClause[];
  parameterChanges?: ParameterChange[];
}

/**
 * Left panel of the three-panel drill-down view.
 * Displays contract language governing the current calculation step,
 * styled as legal document prose with highlighted parameters.
 */
export default function ContractPanel({ clauses, parameterChanges }: ContractPanelProps) {
  const changedParams = new Set(parameterChanges?.map((p) => p.name) ?? []);

  /**
   * Highlight known parameter names in clause text.  Words wrapped in
   * curly braces (e.g. {minimum_enrollment_months}) or that match a known
   * changed parameter name are rendered in bold / colored.
   */
  function renderClauseText(text: string) {
    // Match {param_name} tokens or bare known-parameter names
    const paramPattern = /\{([^}]+)\}/g;
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = paramPattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      const paramName = match[1];
      const change = parameterChanges?.find((p) => p.name === paramName);
      if (change) {
        parts.push(
          <span key={match.index} className="inline-flex items-center gap-1">
            <span className="line-through text-gray-400 text-sm">
              {String(change.defaultValue)}
            </span>
            <span className="font-semibold text-brand-700 bg-brand-50 px-1 rounded">
              {String(change.currentValue)}
            </span>
          </span>,
        );
      } else {
        parts.push(
          <span key={match.index} className="font-semibold text-gray-900">
            {paramName}
          </span>,
        );
      }
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  }

  if (clauses.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400 text-sm">
        No contract clauses available for this step.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <h3 className="text-sm font-semibold text-gray-900">Contract Language</h3>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          The governing contract clauses for this calculation
        </p>
      </div>

      {/* Parameter changes summary */}
      {parameterChanges && parameterChanges.length > 0 && (
        <div className="flex-shrink-0 border-b border-amber-200 bg-amber-50 px-4 py-2">
          <p className="text-xs font-medium text-amber-800 mb-1">Modified Parameters</p>
          <div className="space-y-0.5">
            {parameterChanges.map((change) => (
              <div key={change.name} className="flex items-center gap-2 text-xs">
                <span className="text-amber-700 font-mono">{change.name}</span>
                <span className="text-gray-400 line-through">{String(change.defaultValue)}</span>
                <svg className="h-3 w-3 text-amber-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
                <span className="font-semibold text-amber-900">{String(change.currentValue)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clause list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {clauses.map((clause, idx) => (
          <div key={clause.id || idx} className="group">
            {/* Clause ID label */}
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">
                {clause.id}
              </span>
              {clause.section && (
                <span className="text-[10px] text-gray-400">
                  -- {clause.section}
                </span>
              )}
            </div>

            {/* Clause body as indented blockquote */}
            <blockquote
              className={classNames(
                'border-l-3 pl-4 py-2 text-sm leading-relaxed text-gray-700',
                changedParams.size > 0
                  ? 'border-amber-400 bg-amber-50/50'
                  : 'border-gray-300 bg-white',
              )}
            >
              {renderClauseText(clause.text)}
            </blockquote>

            {clause.title && (
              <p className="mt-1 text-xs font-medium text-gray-500 pl-4">
                {clause.title}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
