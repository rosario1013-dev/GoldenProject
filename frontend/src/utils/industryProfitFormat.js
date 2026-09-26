import { getRateClassName } from './rateStyle';
import { formatFinance } from './formatFinance';

const STATUS_LABELS = {
  PROFITABLE: '盈利',
  BASE_PROFIT_NON_POSITIVE: '基期非正',
  TURNED_PROFITABLE: '扭亏为盈',
  PROFIT_TO_LOSS: '转为亏损',
  LOSS_TO_LOSS: '持续亏损',
};

/** Growth already stored as percent points (42.8 = +42.8%). */
export function formatGrowthPct(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A';
  const num = Number(value);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(digits)}%`;
}

export function formatScore(value, digits = 0) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
}

export function formatProfit(value) {
  return formatFinance(value);
}

export function formatAddedProfit(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  const prefix = num > 0 ? '+' : '';
  return `${prefix}${formatFinance(num)}`;
}

export function formatContribution(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Number(value).toFixed(digits)}%`;
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status || '—';
}

export function growthClassName(value) {
  return getRateClassName(value);
}

export function growthMetricValue(row, period) {
  if (!row) return null;
  if (period === '3y') return row.profit_cagr_3y;
  if (period === '5y') return row.profit_cagr_5y;
  return row.profit_growth_yoy;
}

export function periodLabel(period) {
  if (period === '3y') return '3Y CAGR';
  if (period === '5y') return '5Y CAGR';
  return 'YoY';
}
