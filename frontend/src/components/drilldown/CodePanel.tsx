import { useEffect, useState } from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import { vs } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { getSourceCode } from '@/api/client';
import { classNames } from '@/utils/formatters';

// Register just the Python language to keep the bundle small
SyntaxHighlighter.registerLanguage('python', python);

interface CodeReference {
  module: string;
  function: string;
  function_name?: string;
  lines: string;
  start_line?: number;
  end_line?: number;
}

interface CodePanelProps {
  codeReferences: CodeReference[];
}

interface LoadedCode {
  module: string;
  functionName: string;
  source: string;
  startLine: number;
  endLine: number;
  highlightStart?: number;
  highlightEnd?: number;
}

/**
 * Right panel of the three-panel drill-down view.
 * Shows the actual Python source code that executed the calculation,
 * with the key lines highlighted.
 */
export default function CodePanel({ codeReferences }: CodePanelProps) {
  const [loadedCode, setLoadedCode] = useState<LoadedCode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (codeReferences.length === 0) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    async function fetchAll() {
      try {
        const results = await Promise.all(
          codeReferences.map(async (ref) => {
            const moduleName = ref.module;
            const funcName = ref.function_name || ref.function;
            const resp = await getSourceCode(moduleName, funcName);

            // Parse line range for highlighting (e.g. "45-67")
            let highlightStart: number | undefined;
            let highlightEnd: number | undefined;
            if (ref.lines) {
              const parts = ref.lines.split('-').map(Number);
              if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                highlightStart = parts[0];
                highlightEnd = parts[1];
              }
            } else if (ref.start_line && ref.end_line) {
              highlightStart = ref.start_line;
              highlightEnd = ref.end_line;
            }

            return {
              module: moduleName,
              functionName: funcName,
              source: resp.source,
              startLine: resp.start_line,
              endLine: resp.end_line,
              highlightStart,
              highlightEnd,
            };
          }),
        );
        if (!cancelled) {
          setLoadedCode(results);
          setActiveIndex(0);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load source code');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => {
      cancelled = true;
    };
  }, [codeReferences]);

  const active = loadedCode[activeIndex];

  // Build a custom style that highlights specific lines
  function lineProps(lineNumber: number): React.HTMLProps<HTMLElement> {
    if (
      active?.highlightStart &&
      active?.highlightEnd &&
      lineNumber >= active.highlightStart - active.startLine + 1 &&
      lineNumber <= active.highlightEnd - active.startLine + 1
    ) {
      return {
        style: {
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderLeft: '3px solid #3b82f6',
          marginLeft: '-3px',
          display: 'block',
        },
      };
    }
    return {
      style: { display: 'block' },
    };
  }

  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-gray-50 px-4 py-3">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-emerald-600" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
          </svg>
          <h3 className="text-sm font-semibold text-gray-900">Source Code</h3>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          The Python code that executed this calculation
        </p>
      </div>

      {/* Function tabs when multiple code references exist */}
      {loadedCode.length > 1 && (
        <div className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-1 flex gap-1 overflow-x-auto">
          {loadedCode.map((code, i) => (
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className={classNames(
                'px-2.5 py-1 text-xs font-mono rounded-md transition-colors whitespace-nowrap',
                i === activeIndex
                  ? 'bg-emerald-50 text-emerald-700 font-semibold'
                  : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700',
              )}
            >
              {code.functionName}
            </button>
          ))}
        </div>
      )}

      {/* Code display area */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Loading source code...
            </div>
          </div>
        )}

        {error && (
          <div className="m-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {!loading && !error && active && (
          <div className="flex flex-col">
            {/* Module + function label */}
            <div className="sticky top-0 z-10 bg-white border-b border-gray-100 px-4 py-2">
              <div className="flex items-center gap-1.5 text-xs">
                <span className="font-mono text-gray-400">{active.module}</span>
                <span className="text-gray-300">/</span>
                <span className="font-mono font-semibold text-emerald-700">
                  {active.functionName}()
                </span>
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5">
                Lines {active.startLine}--{active.endLine}
                {active.highlightStart && active.highlightEnd && (
                  <span className="ml-2 text-blue-500">
                    Key logic: L{active.highlightStart}--{active.highlightEnd}
                  </span>
                )}
              </div>
            </div>

            {/* Syntax highlighted code */}
            <div className="text-[13px] leading-5">
              <SyntaxHighlighter
                language="python"
                style={vs}
                showLineNumbers
                startingLineNumber={active.startLine}
                wrapLines
                lineProps={lineProps}
                customStyle={{
                  margin: 0,
                  padding: '12px 0',
                  background: 'transparent',
                  fontSize: '13px',
                  lineHeight: '1.5',
                }}
                lineNumberStyle={{
                  minWidth: '3em',
                  paddingRight: '1em',
                  color: '#9ca3af',
                  fontSize: '11px',
                }}
              >
                {active.source}
              </SyntaxHighlighter>
            </div>

            {/* Footer note */}
            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50/50">
              <p className="text-[11px] text-gray-400 leading-relaxed">
                This is the actual calculation code. The same code runs for every member
                in the population. Contract parameters are injected as configuration --
                the logic itself is deterministic and auditable.
              </p>
            </div>
          </div>
        )}

        {!loading && !error && codeReferences.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <svg className="h-10 w-10 mb-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
            </svg>
            <p className="text-sm">No code references available for this step.</p>
          </div>
        )}
      </div>
    </div>
  );
}
