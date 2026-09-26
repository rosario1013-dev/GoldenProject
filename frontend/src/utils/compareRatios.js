export const COMPARE_FSA_FIELDS = [
  { key: 'ROE', label: 'ROE', percent: true },
  { key: 'ROA', label: 'ROA', percent: true },
  { key: '归母净利润同比_1Y', label: '净利同比1Y', percent: true },
  { key: '归母净利润同比', label: '净利同比', percent: true },
  { key: '营业总收入同比_1Y', label: '收入同比1Y', percent: true },
  { key: '营业总收入同比', label: '收入同比', percent: true },
  { key: '营业总收入_单季同比', label: '收入单季同比', percent: true },
  { key: '每股流动资产', label: '每股流动资产', percent: false },
  { key: 'FQ每股流动资产', label: 'FQ每股流动资产', percent: false },
  { key: 'FQ每股净流动资产', label: 'FQ每股净流动资产', percent: false },
  { key: 'PKV', label: 'PKV', percent: false },
  { key: '毛利率', label: '毛利率', percent: true },
  { key: '管理费用比例', label: '管理费用比例', percent: true },
  { key: '销售费用比例', label: '销售费用比例', percent: true },
  { key: '研发费用比例', label: '研发费用比例', percent: true },
  { key: '营业成本比例', label: '营业成本比例', percent: true },
  { key: 'BPS', label: 'BPS', percent: false },
];

export const COMPARE_CHG_FIELDS = [
  { key: 'chg_1d', label: '一日涨幅', percent: true },
  { key: 'chg_3d', label: '三日涨幅', percent: true },
  { key: 'chg_5d', label: '五日涨幅', percent: true },
  { key: 'chg_1m', label: '一月涨幅', percent: true },
  { key: 'chg_1y', label: '一年涨幅', percent: true },
];

export function medianOf(values) {
  const nums = values.filter((v) => v != null && !Number.isNaN(Number(v))).map(Number);
  if (!nums.length) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

export function comparePosition(value, benchmark) {
  if (value == null || benchmark == null || Number.isNaN(Number(value)) || Number.isNaN(Number(benchmark))) {
    return null;
  }
  const num = Number(value);
  const base = Number(benchmark);
  if (num > base) return 'ahead';
  if (num < base) return 'behind';
  return 'equal';
}

export function formatCompareValue(value, { percent = false } = {}) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  if (percent) {
    const sign = num > 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
  }
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}
