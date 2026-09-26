/** 均线配置（按 K 线根数） */
export const MA_CONFIGS = [
  { period: 5, color: '#f5a623', label: 'MA5' },
  { period: 10, color: '#9b59b6', label: 'MA10' },
  { period: 20, color: '#2f7ed8', label: 'MA20' },
  { period: 60, color: '#27ae60', label: 'MA60' },
];

/** 成交量均线（叠在量柱同一价格轴） */
export const VOLUME_MA_CONFIGS = [
  { period: 5, color: '#f5a623', label: 'VMA5' },
  { period: 10, color: '#2f7ed8', label: 'VMA10' },
];

/** 首屏默认可见 K 线根数 */
export const INITIAL_VISIBLE_BARS = {
  daily: 200,
  weekly: 78,
  monthly: 18,
  quarterly: 6,
  yearly: 15,
};

/** 右侧空白占可视宽度约 1/4，使 K 线约占 3/4 */
export function initialRightOffset(period) {
  const target = INITIAL_VISIBLE_BARS[period] ?? 100;
  return Math.max(4, Math.round(target / 3));
}

export function calcMA(candles, window) {
  if (!candles?.length || window < 1) return [];

  const result = [];
  let sum = 0;

  for (let i = 0; i < candles.length; i += 1) {
    sum += candles[i].close;
    if (i >= window) {
      sum -= candles[i - window].close;
    }
    if (i >= window - 1) {
      result.push({
        time: candles[i].time,
        value: sum / window,
      });
    }
  }

  return result;
}

/** 成交量简单移动平均；`volumes` 为 `{ time, value }` 序列 */
export function calcVolumeMA(volumes, window) {
  if (!volumes?.length || window < 1) return [];

  const result = [];
  let sum = 0;

  for (let i = 0; i < volumes.length; i += 1) {
    sum += volumes[i].value ?? 0;
    if (i >= window) {
      sum -= volumes[i - window].value ?? 0;
    }
    if (i >= window - 1) {
      result.push({
        time: volumes[i].time,
        value: sum / window,
      });
    }
  }

  return result;
}

export function applyInitialVisibleRange(timeScale, totalBars, period) {
  const target = INITIAL_VISIBLE_BARS[period] ?? 100;
  const rightPad = initialRightOffset(period);

  if (totalBars <= 0) return;

  if (totalBars <= target) {
    timeScale.setVisibleLogicalRange({
      from: 0,
      to: totalBars - 1 + rightPad,
    });
    return;
  }

  timeScale.setVisibleLogicalRange({
    from: totalBars - target,
    to: totalBars - 1 + rightPad,
  });
}

/** 日线图键盘缩放：↑ 放大（可见 K 线更少），↓ 缩小 */
export const DAILY_ZOOM_MIN_BARS = 40;
export const DAILY_ZOOM_FACTOR = 0.88;

/** 将 lightweight-charts 时间格式化为 YYYY-MM-DD */
export function formatChartDate(time) {
  if (typeof time === 'string') {
    return time.slice(0, 10);
  }
  if (time && typeof time === 'object' && 'year' in time) {
    const month = String(time.month).padStart(2, '0');
    const day = String(time.day).padStart(2, '0');
    return `${time.year}-${month}-${day}`;
  }
  return String(time ?? '');
}

/** Axis ticks stay date-only; `formatCrosshairTime` only customizes the vertical crosshair label. */
export function getTimeAxisChartOptions(options = {}) {
  const formatDate = (time) => formatChartDate(time);
  return {
    localization: {
      dateFormat: 'yyyy-MM-dd',
      timeFormatter: options.formatCrosshairTime ?? formatDate,
    },
    timeScale: {
      tickMarkFormatter: formatDate,
    },
    crosshair: {
      vertLine: {
        labelVisible: true,
      },
    },
  };
}

/** @deprecated 使用 getTimeAxisChartOptions */
export function getDailyChartOptions() {
  return getTimeAxisChartOptions();
}

export function clampTooltipPosition(point, stageWidth, stageHeight, tooltipWidth = 240, tooltipHeight = 300) {
  let x = point.x + 14;
  let y = point.y - tooltipHeight / 2;

  if (x + tooltipWidth > stageWidth - 8) {
    x = point.x - tooltipWidth - 14;
  }
  if (x < 8) {
    x = 8;
  }
  if (y < 8) {
    y = 8;
  }
  if (y + tooltipHeight > stageHeight - 8) {
    y = stageHeight - tooltipHeight - 8;
  }

  return { x, y };
}

export function applyDailyZoom(timeScale, { centerIndex, totalBars, zoomIn }) {
  const visible = timeScale.getVisibleLogicalRange();
  if (!visible || totalBars <= 1) return;

  const center = centerIndex >= 0 ? centerIndex : (visible.from + visible.to) / 2;
  let span = visible.to - visible.from;

  if (zoomIn) {
    span = Math.max(DAILY_ZOOM_MIN_BARS, span * DAILY_ZOOM_FACTOR);
  } else {
    span = Math.min(totalBars - 1, span / DAILY_ZOOM_FACTOR);
  }

  let from = center - span / 2;
  let to = center + span / 2;

  if (to - from < DAILY_ZOOM_MIN_BARS) {
    to = from + DAILY_ZOOM_MIN_BARS;
  }

  if (from < 0) {
    to -= from;
    from = 0;
  }
  if (to > totalBars - 1) {
    from -= to - (totalBars - 1);
    to = totalBars - 1;
  }

  from = Math.max(0, from); 
  to = Math.min(totalBars - 1, to);

  timeScale.setVisibleLogicalRange({ from, to });
}
