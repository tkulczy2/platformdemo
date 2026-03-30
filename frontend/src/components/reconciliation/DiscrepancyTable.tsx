import { useState, useMemo } from 'react';
import { Discrepancy } from '@/types';
import { formatCurrency, classNames } from '@/utils/formatters';
import DiscrepancyDetail from './DiscrepancyDetail';

interface DiscrepancyTableProps {
  discrepancies: Discrepancy[];
}

type SortField = 'category' | 'subcategory' | 'platform_value' | 'payer_value' | 'financial_impact' | 'member_id';
type SortDir = 'asc' | 'desc';

const CATEGORY_BADGE: Record<string, { label: string; classes: string }> = {
  attribution: { label: 'Attribution', classes: 'bg-blue-100 text-blue-800' },
  quality: { label: 'Quality', classes: 'bg-purple-100 text-purple-800' },
  cost: { label: 'Cost', classes: 'bg-orange-100 text-orange-800' },
};

const SUBCATEGORY_BADGE: Record<string, { label: string; classes: string }> = {
  data_difference: { label: 'Data Difference', classes: 'bg-blue-50 text-blue-700' },
  methodology_difference: { label: 'Methodology', classes: 'bg-purple-50 text-purple-700' },
  timing_difference: { label: 'Timing', classes: 'bg-orange-50 text-orange-700' },
  specification_ambiguity: { label: 'Spec Ambiguity', classes: 'bg-yellow-50 text-yellow-700' },
  platform_only: { label: 'Platform Only', classes: 'bg-blue-50 text-blue-700' },
  payer_only: { label: 'Payer Only', classes: 'bg-amber-50 text-amber-700' },
  different_provider: { label: 'Diff Provider', classes: 'bg-indigo-50 text-indigo-700' },
  ehr_only_data: { label: 'EHR Only', classes: 'bg-teal-50 text-teal-700' },
  payer_exclusion: { label: 'Payer Exclusion', classes: 'bg-red-50 text-red-700' },
  screening_conflict: { label: 'Screening Conflict', classes: 'bg-pink-50 text-pink-700' },
  runout_timing: { label: 'Run-out Timing', classes: 'bg-orange-50 text-orange-700' },
  amount_difference: { label: 'Amount Diff', classes: 'bg-yellow-50 text-yellow-700' },
};

const ALL_CATEGORIES = ['attribution', 'quality', 'cost'] as const;

export default function DiscrepancyTable({ discrepancies }: DiscrepancyTableProps) {
  const [sortField, setSortField] = useState<SortField>('financial_impact');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!categoryFilter) return discrepancies;
    return discrepancies.filter((d) => d.category === categoryFilter);
  }, [discrepancies, categoryFilter]);

  const sorted = useMemo(() => {
    const list = [...filtered];
    list.sort((a, b) => {
      let aVal: string | number = '';
      let bVal: string | number = '';

      switch (sortField) {
        case 'category':
          aVal = a.category;
          bVal = b.category;
          break;
        case 'subcategory':
          aVal = a.subcategory;
          bVal = b.subcategory;
          break;
        case 'platform_value':
          aVal = typeof a.platform_value === 'number' ? a.platform_value : String(a.platform_value ?? '');
          bVal = typeof b.platform_value === 'number' ? b.platform_value : String(b.platform_value ?? '');
          break;
        case 'payer_value':
          aVal = typeof a.payer_value === 'number' ? a.payer_value : String(a.payer_value ?? '');
          bVal = typeof b.payer_value === 'number' ? b.payer_value : String(b.payer_value ?? '');
          break;
        case 'financial_impact':
          aVal = Math.abs(a.financial_impact);
          bVal = Math.abs(b.financial_impact);
          break;
        case 'member_id':
          aVal = a.member_id;
          bVal = b.member_id;
          break;
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return list;
  }, [filtered, sortField, sortDir]);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'financial_impact' ? 'desc' : 'asc');
    }
  }

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) {
      return (
        <svg className="ml-1 h-3.5 w-3.5 text-gray-400 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    return (
      <svg className="ml-1 h-3.5 w-3.5 text-brand-600 inline" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        {sortDir === 'asc' ? (
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        )}
      </svg>
    );
  }

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const d of discrepancies) {
      counts[d.category] = (counts[d.category] ?? 0) + 1;
    }
    return counts;
  }, [discrepancies]);

  return (
    <div className="space-y-4">
      {/* Category filter buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider mr-1">Filter:</span>
        <button
          onClick={() => setCategoryFilter(null)}
          className={classNames(
            'rounded-full px-3 py-1 text-xs font-medium transition-colors',
            !categoryFilter
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
          )}
        >
          All ({discrepancies.length})
        </button>
        {ALL_CATEGORIES.map((cat) => {
          const badge = CATEGORY_BADGE[cat];
          const count = categoryCounts[cat] ?? 0;
          if (count === 0) return null;
          return (
            <button
              key={cat}
              onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              className={classNames(
                'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                categoryFilter === cat
                  ? 'bg-gray-900 text-white'
                  : classNames(badge.classes, 'hover:opacity-80'),
              )}
            >
              {badge.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('category')}>
                Category <SortIcon field="category" />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('subcategory')}>
                Type <SortIcon field="subcategory" />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('member_id')}>
                Member <SortIcon field="member_id" />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('platform_value')}>
                Platform <SortIcon field="platform_value" />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('payer_value')}>
                Payer <SortIcon field="payer_value" />
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none" onClick={() => handleSort('financial_impact')}>
                Impact <SortIcon field="financial_impact" />
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((d) => {
              const isExpanded = expandedId === d.id;
              const badge = CATEGORY_BADGE[d.category] ?? { label: d.category, classes: 'bg-gray-100 text-gray-700' };
              const subBadge = SUBCATEGORY_BADGE[d.subcategory] ?? { label: d.subcategory, classes: 'bg-gray-50 text-gray-600' };
              const isPositive = d.financial_impact > 0;

              return (
                <tr key={d.id} className="group">
                  <td colSpan={7} className="p-0">
                    {/* Row content */}
                    <div
                      className={classNames(
                        'grid grid-cols-[1fr_1fr_1fr_1fr_1fr_auto_auto] items-center gap-0 px-0 transition-colors',
                        isExpanded ? 'bg-gray-50' : 'hover:bg-gray-50/50',
                      )}
                    >
                      <div className="px-4 py-3">
                        <span className={classNames('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', badge.classes)}>
                          {badge.label}
                        </span>
                      </div>
                      <div className="px-4 py-3">
                        <span className={classNames('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', subBadge.classes)}>
                          {subBadge.label}
                        </span>
                      </div>
                      <div className="px-4 py-3">
                        <span className="text-xs font-mono text-gray-700">{d.member_id}</span>
                      </div>
                      <div className="px-4 py-3">
                        <span className="text-sm text-gray-900">
                          {d.platform_value != null ? String(d.platform_value) : '--'}
                        </span>
                      </div>
                      <div className="px-4 py-3">
                        <span className="text-sm text-gray-900">
                          {d.payer_value != null ? String(d.payer_value) : '--'}
                        </span>
                      </div>
                      <div className="px-4 py-3 text-right min-w-[100px]">
                        <span className={classNames(
                          'text-sm font-semibold',
                          isPositive ? 'text-emerald-700' : 'text-red-700',
                        )}>
                          {isPositive ? '+' : ''}{formatCurrency(d.financial_impact)}
                        </span>
                      </div>
                      <div className="px-4 py-3 text-center min-w-[100px]">
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : d.id)}
                          className={classNames(
                            'inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                            isExpanded
                              ? 'bg-brand-100 text-brand-700'
                              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-800',
                          )}
                        >
                          {isExpanded ? 'Hide' : 'View Detail'}
                          <svg
                            className={classNames('h-3.5 w-3.5 transition-transform', isExpanded && 'rotate-180')}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* Expanded detail */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-1">
                        <DiscrepancyDetail discrepancy={d} />
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}

            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-500">
                  No discrepancies found for the selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      <div className="flex items-center justify-between text-sm text-gray-500 px-1">
        <span>
          Showing {sorted.length} of {discrepancies.length} discrepancies
        </span>
        <span className="font-medium">
          Net impact: {' '}
          <span className={classNames(
            'font-semibold',
            filtered.reduce((s, d) => s + d.financial_impact, 0) >= 0 ? 'text-emerald-700' : 'text-red-700',
          )}>
            {formatCurrency(filtered.reduce((s, d) => s + d.financial_impact, 0))}
          </span>
        </span>
      </div>
    </div>
  );
}
