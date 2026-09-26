import { CHART, TEXT } from './theme';

/** CSS class for rate/change cells (A-share: red up, green down). */
export function getRateClassName(value) {
  if (value == null || Number.isNaN(Number(value))) return 'rate-cell';
  const num = Number(value);
  if (num > 0) return 'rate-cell rate-cell--up';
  if (num < 0) return 'rate-cell rate-cell--down';
  return 'rate-cell rate-cell--neutral';
}

/** Inline color for rate/change values (YoY sub-lines, charts). */
export function getRateColor(value) {
  if (value == null || value === 0 || Number.isNaN(Number(value))) return TEXT.muted;
  return Number(value) > 0 ? CHART.up : CHART.down;
}

export function formatSignedPct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(digits)}%`;
}

export function formatPct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(digits)}%`;
}
