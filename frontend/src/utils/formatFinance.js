function trimZeros(str) {
  if (!str.includes('.')) return str;
  return str.replace(/\.?0+$/, '');
}

/** is_percent 指标：后端以小数存储，展示时乘 100 */
export function toPercentDisplay(value) {
  return Number(value) * 100;
}

/**
 * 中文财报数字格式化：亿 / 万 / 元，并去除多余尾零。
 */
export function formatFinance(value, { isPercent = false, maxDecimals = 2 } = {}) {
  if (value == null || Number.isNaN(value)) return '--';
  if (value === 0) return isPercent ? '0%' : '0';

  const num = Number(value);
  const sign = num < 0 ? '-' : '';
  const abs = Math.abs(num);

  if (isPercent) {
    return `${sign}${trimZeros(toPercentDisplay(abs).toFixed(maxDecimals))}%`;
  }

  if (abs < 10000) {
    return `${sign}${trimZeros(abs.toFixed(maxDecimals))}`;
  }

  let scaled;
  let unit;
  if (abs >= 1e8) {
    scaled = abs / 1e8;
    unit = '亿';
  } else {
    scaled = abs / 1e4;
    unit = '万';
  }

  return `${sign}${trimZeros(scaled.toFixed(maxDecimals))}${unit}`;
}

/** 悬停提示用的完整原值 */
export function formatFinanceRaw(value, { isPercent = false } = {}) {
  if (value == null || Number.isNaN(value)) return '';
  const displayValue = isPercent ? toPercentDisplay(value) : Number(value);
  const formatted = displayValue.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return isPercent ? `${formatted}%` : formatted;
}
