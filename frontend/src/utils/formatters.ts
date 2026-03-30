/**
 * Formatting utilities for the VBC Performance Intelligence UI.
 */

/**
 * Format a number as US currency (e.g. $1,234.56).
 */
export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a decimal as a percentage (e.g. 0.854 -> "85.4%").
 * If the value is already > 1, it is treated as a raw percentage.
 */
export function formatPercent(value: number, decimals = 1): string {
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(decimals)}%`;
}

/**
 * Format a number with locale-aware thousands separators.
 */
export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format an ISO date string to a human-readable form (e.g. "Jan 15, 2025").
 */
export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * Tailwind-style classNames helper. Filters out falsy values and joins with spaces.
 *
 * Usage: classNames('px-4', isActive && 'bg-blue-500', disabled && 'opacity-50')
 */
export function classNames(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}
