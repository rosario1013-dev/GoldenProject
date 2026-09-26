import { getRateColor } from './rateStyle';

const QUARTER_SUFFIXES = ['-03-31', '-06-30', '-09-30', '-12-31'];

export const DEFAULT_VISIBLE_FROM_YEAR = 2015;

export const PERIOD_MODES = {
  QUARTER: 'quarter',
  YEAR: 'year',
};

export function isQuarterEndColumn(col) {
  return QUARTER_SUFFIXES.some((suffix) => col.endsWith(suffix));
}

export function isYearEndColumn(col) {
  return col.endsWith('-12-31');
}

export function filterColumnsByPeriod(columns, periodMode) {
  if (!columns?.length) return [];
  if (periodMode === PERIOD_MODES.YEAR) {
    return columns.filter(isYearEndColumn);
  }
  return columns.filter(isQuarterEndColumn);
}

export function getColumnYear(col) {
  const match = col.match(/^(\d{4})-/);
  return match ? Number(match[1]) : null;
}

/** 按年份切分：默认展示 cutoffYear 及以后，更早的归入折叠区 */
export function splitColumnsByYearCutoff(columns, cutoffYear = DEFAULT_VISIBLE_FROM_YEAR) {
  const recent = [];
  const older = [];
  for (const col of columns) {
    const year = getColumnYear(col);
    if (year != null && year < cutoffYear) {
      older.push(col);
    } else {
      recent.push(col);
    }
  }
  return { recent, older };
}

export function resolveDisplayColumns(periodColumns, { showOlder = false, cutoffYear = DEFAULT_VISIBLE_FROM_YEAR } = {}) {
  const { recent, older } = splitColumnsByYearCutoff(periodColumns, cutoffYear);
  if (showOlder && older.length) {
    return [...recent, ...older];
  }
  return recent;
}

export function formatColumnTitle(col, periodMode) {
  if (periodMode === PERIOD_MODES.YEAR && isYearEndColumn(col)) {
    return col.slice(0, 4);
  }
  return col;
}

export function getPriorYearColumn(col, allColumns) {
  const match = col.match(/^(\d{4})-(\d{2}-\d{2})$/);
  if (!match) return null;
  const priorCol = `${Number(match[1]) - 1}-${match[2]}`;
  return allColumns.includes(priorCol) ? priorCol : null;
}

export function calcYoYChange(current, prior, isPercent) {
  if (current == null || prior == null || Number.isNaN(current) || Number.isNaN(prior)) {
    return null;
  }
  if (isPercent) {
    return (current - prior) * 100;
  }
  if (prior === 0) return null;
  return ((current - prior) / Math.abs(prior)) * 100;
}

function trimZeros(str) {
  if (!str.includes('.')) return str;
  return str.replace(/\.?0+$/, '');
}

export function formatYoYChange(change, isPercent) {
  if (change == null || Number.isNaN(change)) return null;
  const sign = change > 0 ? '+' : '';
  if (isPercent) {
    return `${sign}${trimZeros(change.toFixed(2))}ppt`;
  }
  return `${sign}${trimZeros(change.toFixed(2))}%`;
}

export function getYoYColor(change) {
  return getRateColor(change);
}
