export const SURFACE = {
  base: '#0b1220',
  container: '#111827',
  elevated: '#1a2332',
};

export const TEXT = {
  primary: '#e5e7eb',
  body: '#d1d5db',
  muted: '#9ca3af',
};

export const ACCENT = {
  primary: '#1677ff',
  soft: 'rgba(22,119,255,0.15)',
  border: '#60a5fa',
};

export const BORDER = {
  subtle: 'rgba(255,255,255,0.08)',
  chart: '#334155',
};

export const CHART = {
  grid: '#1f2937',
  bg: '#111827',
  heatmapBg: '#111',
  up: '#cf1322',
  down: '#389e0d',
  neutral: '#546e7a',
};

/** Shared dark-theme defaults for ECharts option objects. */
export function darkEchartsBase() {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: TEXT.muted },
    legend: { textStyle: { color: TEXT.muted } },
    tooltip: {
      backgroundColor: SURFACE.container,
      borderColor: BORDER.chart,
      textStyle: { color: TEXT.body },
    },
  };
}

export function darkAxisStyle() {
  return {
    axisLine: { lineStyle: { color: BORDER.chart } },
    axisLabel: { color: TEXT.muted },
    nameTextStyle: { color: TEXT.muted },
  };
}

export function darkSplitLine() {
  return { lineStyle: { color: CHART.grid, type: 'dashed' } };
}
