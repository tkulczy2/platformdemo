import { useCallback } from 'react';
import { classNames } from '@/utils/formatters';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ClauseParameter {
  key: string;
  label: string;
  type: 'dropdown' | 'number' | 'currency' | 'percentage' | 'toggle' | 'checkbox-list';
  value: unknown;
  options?: { label: string; value: string }[];
  /** For checkbox-list: available items with labels */
  items?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
}

export interface ClauseData {
  id: string;
  title: string;
  text: string;
  linkedStep: number;
  linkedStepName: string;
  parameters: ClauseParameter[];
}

interface ClauseCardProps {
  clause: ClauseData;
  modifiedKeys: Set<string>;
  onChange: (paramKey: string, value: unknown) => void;
}

// ---------------------------------------------------------------------------
// Step badge color mapping
// ---------------------------------------------------------------------------

const STEP_COLORS: Record<number, string> = {
  1: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  2: 'bg-violet-50 text-violet-700 ring-violet-600/20',
  3: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  4: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  5: 'bg-rose-50 text-rose-700 ring-rose-600/20',
  6: 'bg-cyan-50 text-cyan-700 ring-cyan-600/20',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ClauseCard({ clause, modifiedKeys, onChange }: ClauseCardProps) {
  const stepColor = STEP_COLORS[clause.linkedStep] ?? 'bg-gray-50 text-gray-700 ring-gray-600/20';

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-gray-400">{clause.id}</span>
          <h3 className="text-sm font-semibold text-gray-900">{clause.title}</h3>
        </div>
        <span
          className={classNames(
            'inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset',
            stepColor,
          )}
        >
          Step {clause.linkedStep}: {clause.linkedStepName}
        </span>
      </div>

      {/* Contract language */}
      <div className="px-5 py-4">
        <div className="border-l-4 border-brand-200 bg-gray-50 rounded-r-md px-4 py-3">
          <p className="text-sm leading-relaxed text-gray-700 italic">{clause.text}</p>
        </div>
      </div>

      {/* Parameters */}
      {clause.parameters.length > 0 && (
        <div className="border-t border-gray-100 px-5 py-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
            Configurable Parameters
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {clause.parameters.map((param) => (
              <ParameterField
                key={param.key}
                param={param}
                isModified={modifiedKeys.has(param.key)}
                onChange={onChange}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Parameter field renderer
// ---------------------------------------------------------------------------

interface ParameterFieldProps {
  param: ClauseParameter;
  isModified: boolean;
  onChange: (key: string, value: unknown) => void;
}

function ParameterField({ param, isModified, onChange }: ParameterFieldProps) {
  const handleChange = useCallback(
    (value: unknown) => onChange(param.key, value),
    [onChange, param.key],
  );

  const labelEl = (
    <label
      htmlFor={`param-${param.key}`}
      className={classNames(
        'mb-1 block text-xs font-medium',
        isModified ? 'text-amber-700' : 'text-gray-600',
      )}
    >
      {param.label}
      {isModified && (
        <span className="ml-1.5 inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
          Changed
        </span>
      )}
    </label>
  );

  const inputBase =
    'block w-full rounded-md border-0 py-1.5 text-sm text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-brand-600 sm:leading-6';
  const modifiedRing = isModified ? 'ring-amber-400 bg-amber-50/50' : '';

  switch (param.type) {
    case 'dropdown':
      return (
        <div>
          {labelEl}
          <select
            id={`param-${param.key}`}
            value={String(param.value)}
            onChange={(e) => handleChange(e.target.value)}
            className={classNames(inputBase, modifiedRing, 'px-3')}
          >
            {param.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      );

    case 'number':
      return (
        <div>
          {labelEl}
          <input
            id={`param-${param.key}`}
            type="number"
            value={Number(param.value)}
            min={param.min}
            max={param.max}
            step={param.step ?? 1}
            onChange={(e) => handleChange(Number(e.target.value))}
            className={classNames(inputBase, modifiedRing, 'px-3')}
          />
        </div>
      );

    case 'currency':
      return (
        <div>
          {labelEl}
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 text-sm">
              $
            </span>
            <input
              id={`param-${param.key}`}
              type="number"
              value={Number(param.value)}
              min={param.min ?? 0}
              step={param.step ?? 0.01}
              onChange={(e) => handleChange(Number(e.target.value))}
              className={classNames(inputBase, modifiedRing, 'pl-7 pr-3')}
            />
          </div>
        </div>
      );

    case 'percentage':
      return (
        <div>
          {labelEl}
          <div className="relative">
            <input
              id={`param-${param.key}`}
              type="number"
              value={Math.round(Number(param.value) * 10000) / 100}
              min={param.min != null ? param.min * 100 : 0}
              max={param.max != null ? param.max * 100 : 100}
              step={param.step ?? 0.5}
              onChange={(e) => handleChange(Number(e.target.value) / 100)}
              className={classNames(inputBase, modifiedRing, 'pl-3 pr-8')}
            />
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 text-sm">
              %
            </span>
          </div>
        </div>
      );

    case 'toggle':
      return (
        <div className="flex items-center gap-3 pt-5">
          <button
            id={`param-${param.key}`}
            type="button"
            role="switch"
            aria-checked={Boolean(param.value)}
            onClick={() => handleChange(!param.value)}
            className={classNames(
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2',
              Boolean(param.value) ? 'bg-brand-600' : 'bg-gray-200',
              isModified && 'ring-2 ring-amber-400 ring-offset-1',
            )}
          >
            <span
              className={classNames(
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                Boolean(param.value) ? 'translate-x-5' : 'translate-x-0',
              )}
            />
          </button>
          <span
            className={classNames(
              'text-xs font-medium',
              isModified ? 'text-amber-700' : 'text-gray-600',
            )}
          >
            {param.label}
            {isModified && (
              <span className="ml-1.5 inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                Changed
              </span>
            )}
          </span>
        </div>
      );

    case 'checkbox-list':
      return (
        <div className="sm:col-span-2">
          {labelEl}
          <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {param.items?.map((item) => {
              const checked = Array.isArray(param.value) && param.value.includes(item.value);
              return (
                <label
                  key={item.value}
                  className={classNames(
                    'flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-xs transition-colors',
                    checked
                      ? 'border-brand-300 bg-brand-50 text-brand-800'
                      : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50',
                    isModified && checked && 'border-amber-300 bg-amber-50',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const current = (Array.isArray(param.value) ? param.value : []) as string[];
                      const next = checked
                        ? current.filter((v) => v !== item.value)
                        : [...current, item.value];
                      handleChange(next);
                    }}
                    className="h-3.5 w-3.5 rounded border-gray-300 text-brand-600 focus:ring-brand-600"
                  />
                  {item.label}
                </label>
              );
            })}
          </div>
        </div>
      );

    default:
      return null;
  }
}
