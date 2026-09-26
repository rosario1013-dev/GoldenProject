import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Checkbox, Segmented, Spin, Tooltip } from 'antd';
import {
  CandlestickSeries,
  createChart,
  createSeriesMarkers,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  LineType,
} from 'lightweight-charts';

import {
  applyDailyZoom,
  applyInitialVisibleRange,
  calcMA,
  calcVolumeMA,
  formatChartDate,
  getTimeAxisChartOptions,
  initialRightOffset,
  MA_CONFIGS,
  VOLUME_MA_CONFIGS,
} from '../utils/chartMa';
import {
  buildIndicatorLookup,
  chartHeightWithIndicators,
  defaultIndicatorEnabled,
  deriveIndicatorStatuses,
  enabledIndicatorKinds,
  formatIndicatorValue,
  INDICATOR_COLORS,
  INDICATOR_OPTIONS,
  paneIndicatorKinds,
  withMacdColors,
} from '../utils/chartIndicators';

const CHART_HEIGHT = 480;

export const CHART_PERIODS = [
  { label: '日线', value: 'daily' },
  { label: '周线', value: 'weekly' },
  { label: '月线', value: 'monthly' },
  { label: '季线', value: 'quarterly' },
  { label: '年线', value: 'yearly' },
];

/** Seasonal stepline overlays from main_FSA (common_FSA.py). */
export const FSA_OVERLAY_LINES = [
  { key: 'BPS', label: 'BPS', color: '#1565c0' },
  { key: '固有PB', label: '固有PB', color: '#c62828' },
  { key: 'C_BPS加5年净利润', label: 'C_BPS加5年净利润', color: '#6a1b9a' },
];

const SWING_BUY_COLOR = '#2e7d32';
const SWING_SELL_COLOR = '#c62828';

function toSwingChartMarkers(markers, candleTimes) {
  const allowed = new Set(candleTimes ?? []);
  const out = [];
  for (const row of markers ?? []) {
    if (!row?.time || !allowed.has(row.time)) continue;
    const isBuy = row.kind === 'low';
    out.push({
      time: row.time,
      position: isBuy ? 'belowBar' : 'aboveBar',
      shape: isBuy ? 'arrowUp' : 'arrowDown',
      color: isBuy ? SWING_BUY_COLOR : SWING_SELL_COLOR,
      size: 1.4,
    });
  }
  return out;
}
function pickNum(...values) {
  for (const value of values) {
    if (value != null && !Number.isNaN(Number(value))) return Number(value);
  }
  return null;
}

function toSeriesData(records, { useRaw = false } = {}) {
  const candles = [];
  const volumes = [];

  for (const row of records) {
    const open = useRaw ? pickNum(row.raw_open, row.open) : pickNum(row.open);
    const high = useRaw ? pickNum(row.raw_high, row.high) : pickNum(row.high);
    const low = useRaw ? pickNum(row.raw_low, row.low) : pickNum(row.low);
    const close = useRaw ? pickNum(row.raw_close, row.close) : pickNum(row.close);
    const volume = useRaw ? pickNum(row.raw_volume, row.volume) : pickNum(row.volume);
    if (open == null || high == null || low == null || close == null) continue;

    const up = close >= open;
    candles.push({ time: row.dt, open, high, low, close });
    volumes.push({
      time: row.dt,
      value: volume ?? 0,
      color: up ? 'rgba(239, 83, 80, 0.5)' : 'rgba(38, 166, 154, 0.5)',
    });
  }

  return { candles, volumes };
}

function displayClose(record, useRaw) {
  return useRaw ? pickNum(record.raw_close, record.close) : pickNum(record.close);
}

function formatPrice(value) {
  if (value == null || Number.isNaN(value)) return '--';
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatVolume(value) {
  if (value == null || Number.isNaN(value)) return '--';
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 0 });
}

function formatChangePct(value) {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function calcChangePct(close, prevClose) {
  if (close == null || prevClose == null || Number.isNaN(close) || Number.isNaN(prevClose)) {
    return null;
  }
  if (prevClose === 0) return null;
  return ((close - prevClose) / prevClose) * 100;
}

/** 从该日收盘价到最新收盘价的涨跌幅（不复权）。 */
function calcChangeToNowPct(record, latestRecord) {
  if (!record || !latestRecord) return null;
  return calcChangePct(latestRecord.raw_close, record.raw_close);
}

function formatDateWithChangeToNow(time, records) {
  const date = formatChartDate(time);
  if (!records?.length) return date;
  const timeKey = typeof time === 'string' ? time : date;
  const record = records.find((row) => row.dt === timeKey || formatChartDate(row.dt) === date);
  if (!record) return date;
  const pct = calcChangeToNowPct(record, records[records.length - 1]);
  if (pct == null) return date;
  return `${date} 至今涨幅${formatChangePct(pct)}`;
}

function recordToBarInfo(record, prevRecord = null, indicatorRow = null, latestRecord = null) {
  if (!record) return null;
  const close = record.raw_close;
  const prevClose = prevRecord?.raw_close;
  const changePct = calcChangePct(close, prevClose);
  const changeToNowPct = calcChangeToNowPct(record, latestRecord ?? record);
  return {
    dt: formatChartDate(record.dt),
    open: record.raw_open,
    high: record.raw_high,
    low: record.raw_low,
    close,
    volume: record.raw_volume,
    changePct,
    changeToNowPct,
    indicators: indicatorRow ?? null,
  };
}

function changePctColor(changePct) {
  if (changePct == null || Number.isNaN(changePct) || changePct === 0) return undefined;
  return changePct > 0 ? '#ef5350' : '#26a69a';
}

/** Snap quarterly report dates onto the latest trading day <= REPORTDATE. */
function alignOverlayPoints(points, candleTimes) {
  if (!points?.length) return [];
  const times = candleTimes ?? [];
  const mapped = [];

  for (const point of points) {
    const value = pickNum(point.value);
    const dt = point.dt ? String(point.dt).slice(0, 10) : '';
    if (value == null || !dt) continue;

    if (!times.length) {
      mapped.push({ time: dt, value });
      continue;
    }

    let lo = 0;
    let hi = times.length - 1;
    let best = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (times[mid] <= dt) {
        best = mid;
        lo = mid + 1;
      } else {
        hi = mid - 1;
      }
    }
    if (best >= 0) mapped.push({ time: times[best], value });
  }

  const byTime = new Map();
  for (const pt of mapped) byTime.set(pt.time, pt);
  return Array.from(byTime.values()).sort((a, b) => (a.time < b.time ? -1 : 1));
}

function IndicatorTooltipRows({ indicators, enabled }) {
  if (!indicators || !enabled) return null;
  const rows = [];
  if (enabled.macd) {
    rows.push(
      <div key="macd" className="stock-chart__info-row">
        MACD {formatIndicatorValue(indicators.macd)} / DIF {formatIndicatorValue(indicators.macd_dif)} / DEA{' '}
        {formatIndicatorValue(indicators.macd_dea)}
      </div>,
    );
  }
  if (enabled.rsi) {
    rows.push(
      <div key="rsi" className="stock-chart__info-row">
        RSI6 {formatIndicatorValue(indicators.rsi_6, 1)} / RSI12 {formatIndicatorValue(indicators.rsi_12, 1)} / RSI24{' '}
        {formatIndicatorValue(indicators.rsi_24, 1)}
      </div>,
    );
  }
  if (enabled.kdj) {
    rows.push(
      <div key="kdj" className="stock-chart__info-row">
        K {formatIndicatorValue(indicators.kdj_k, 1)} / D {formatIndicatorValue(indicators.kdj_d, 1)} / J{' '}
        {formatIndicatorValue(indicators.kdj_j, 1)}
      </div>,
    );
  }
  if (enabled.boll) {
    rows.push(
      <div key="boll" className="stock-chart__info-row">
        BOLL {formatIndicatorValue(indicators.boll_mid)} [{formatIndicatorValue(indicators.boll_lower)}–
        {formatIndicatorValue(indicators.boll_upper)}]
      </div>,
    );
  }
  return rows;
}

function MainPaneTooltip({ info, showBoll }) {
  if (!info) return null;
  return (
    <div className="stock-chart__info">
      <div className="stock-chart__info-date">
        {info.dt}{' '}
        <span style={{ color: changePctColor(info.changeToNowPct), fontWeight: 500 }}>
          至今涨幅{formatChangePct(info.changeToNowPct)}
        </span>
      </div>
      <div className="stock-chart__info-row">开 {formatPrice(info.open)}</div>
      <div className="stock-chart__info-row">低 {formatPrice(info.low)}</div>
      <div className="stock-chart__info-row">高 {formatPrice(info.high)}</div>
      <div className="stock-chart__info-row">收 {formatPrice(info.close)}</div>
      <div className="stock-chart__info-row">量 {formatVolume(info.volume)}</div>
      <div className="stock-chart__info-row" style={{ color: changePctColor(info.changePct) }}>
        涨幅 {formatChangePct(info.changePct)}
      </div>
      {showBoll ? (
        <IndicatorTooltipRows indicators={info.indicators} enabled={{ boll: true }} />
      ) : null}
    </div>
  );
}

function IndicatorPaneTooltip({ kind, info, top }) {
  if (!info?.indicators || top == null) return null;
  const enabled = { [kind]: true };
  return (
    <div className="stock-chart__info stock-chart__info--pane" style={{ top }}>
      <IndicatorTooltipRows indicators={info.indicators} enabled={enabled} />
    </div>
  );
}

function ChartPaneTooltips({ info, indicatorEnabled, paneLayouts }) {
  if (!info) return null;
  const byKind = Object.fromEntries((paneLayouts ?? []).map((p) => [p.kind, p]));
  return (
    <>
      <MainPaneTooltip info={info} showBoll={Boolean(indicatorEnabled?.boll)} />
      {indicatorEnabled?.macd && byKind.macd ? (
        <IndicatorPaneTooltip kind="macd" info={info} top={byKind.macd.top + 4} />
      ) : null}
      {indicatorEnabled?.rsi && byKind.rsi ? (
        <IndicatorPaneTooltip kind="rsi" info={info} top={byKind.rsi.top + 4} />
      ) : null}
      {indicatorEnabled?.kdj && byKind.kdj ? (
        <IndicatorPaneTooltip kind="kdj" info={info} top={byKind.kdj.top + 4} />
      ) : null}
    </>
  );
}

function StatusBadges({ badges }) {
  if (!badges?.length) return null;
  return (
    <div className="stock-chart__status">
      {badges.map((badge) => (
        <Tooltip
          key={badge.id}
          title={badge.detail}
          placement="bottomRight"
          mouseEnterDelay={0.15}
        >
          <span className={`stock-chart__status-badge stock-chart__status-badge--${badge.tone}`}>
            {badge.label}
          </span>
        </Tooltip>
      ))}
    </div>
  );
}

function emptyOverlayState() {
  return Object.fromEntries(FSA_OVERLAY_LINES.map((line) => [line.key, false]));
}

export default function StockChart({
  ide,
  height = CHART_HEIGHT,
  fillHeight = false,
  showPeriodSelector = true,
  periods = CHART_PERIODS,
  adjustment = 'forward',
  defaultPeriod = 'daily',
  showFsaContextMenu = true,
  showIndicators = false,
  showSwingMarkersToggle = false,
  defaultShowSwingMarkers = true,
}) {
  const stageRef = useRef(null);
  const containerRef = useRef(null);
  const recordsRef = useRef([]);
  const indicatorLookupRef = useRef(new Map());
  const focusedIndexRef = useRef(-1);
  const chartApiRef = useRef(null);
  const overlayEnabledRef = useRef(emptyOverlayState());
  const fsaSeriesRef = useRef(null);
  const swingMarkersRef = useRef(null);
  const showSwingMarkersRef = useRef(defaultShowSwingMarkers);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState(defaultPeriod);
  const [barInfo, setBarInfo] = useState(null);
  const [overlayEnabled, setOverlayEnabled] = useState(emptyOverlayState);
  const [indicatorEnabled, setIndicatorEnabled] = useState(defaultIndicatorEnabled);
  const [paneLayouts, setPaneLayouts] = useState([]);
  const [statusSnapshot, setStatusSnapshot] = useState(null);
  const [fsaLoading, setFsaLoading] = useState(false);
  const [fsaError, setFsaError] = useState('');
  const [contextMenu, setContextMenu] = useState(null);
  const [showSwingMarkers, setShowSwingMarkers] = useState(defaultShowSwingMarkers);
  const [swingLoading, setSwingLoading] = useState(false);
  const [swingError, setSwingError] = useState('');

  overlayEnabledRef.current = overlayEnabled;
  showSwingMarkersRef.current = showSwingMarkers;
  const swingToggleVisible = showSwingMarkersToggle || showIndicators;
  const fixedHeight = showIndicators
    ? chartHeightWithIndicators(height, indicatorEnabled)
    : height;
  // fillHeight: size follows the container via ResizeObserver; fixed height only seeds fallback.
  const effectiveHeight = fillHeight ? null : fixedHeight;
  const layoutHeightKey = fillHeight ? 'fill' : fixedHeight;
  const activeIndicatorKinds = showIndicators ? enabledIndicatorKinds(indicatorEnabled) : [];
  const indicatorKindsKey = activeIndicatorKinds.join(',');

  const statusBadges = useMemo(() => {
    if (!showIndicators || !statusSnapshot) return [];
    return deriveIndicatorStatuses({
      last: statusSnapshot.last,
      prev: statusSnapshot.prev,
      enabled: indicatorEnabled,
      changePct: statusSnapshot.changePct,
    });
  }, [showIndicators, statusSnapshot, indicatorEnabled]);

  const toggleIndicator = useCallback((key) => {
    setIndicatorEnabled((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const syncSwingMarkers = useCallback(() => {
    const api = chartApiRef.current;
    if (!api?.markersApi) return;
    if (!showSwingMarkersRef.current) {
      api.markersApi.setMarkers([]);
      return;
    }
    api.markersApi.setMarkers(
      toSwingChartMarkers(swingMarkersRef.current?.markers ?? [], api.candleTimes),
    );
  }, []);

  const ensureSwingData = useCallback(() => {
    if (!ide) return Promise.resolve([]);
    const cache = swingMarkersRef.current;
    if (
      cache &&
      cache.ide === ide &&
      cache.period === period &&
      cache.adjustment === adjustment
    ) {
      return Promise.resolve(cache.markers);
    }

    setSwingLoading(true);
    setSwingError('');
    const params = new URLSearchParams({ period, adjustment });
    return fetch(`/api/stock/${encodeURIComponent(ide)}/swings/?${params}`)
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || '买卖点加载失败');
        return payload;
      })
      .then((payload) => {
        const markers = payload.markers ?? [];
        swingMarkersRef.current = { ide, period, adjustment, markers, params: payload.params };
        return markers;
      })
      .catch((err) => {
        setSwingError(err.message);
        swingMarkersRef.current = null;
        throw err;
      })
      .finally(() => setSwingLoading(false));
  }, [ide, period, adjustment]);

  const toggleSwingMarkers = useCallback(() => {
    setShowSwingMarkers((prev) => {
      const next = !prev;
      showSwingMarkersRef.current = next;
      if (!next) {
        requestAnimationFrame(() => syncSwingMarkers());
        return next;
      }
      ensureSwingData()
        .then(() => requestAnimationFrame(() => syncSwingMarkers()))
        .catch(() => {});
      return next;
    });
  }, [ensureSwingData, syncSwingMarkers]);

  const syncOverlaySeries = useCallback(() => {
    const api = chartApiRef.current;
    if (!api?.chart) return;

    const enabled = overlayEnabledRef.current;
    const seriesMap = fsaSeriesRef.current?.series ?? {};
    const candleTimes = api.candleTimes ?? [];

    for (const line of FSA_OVERLAY_LINES) {
      const want = Boolean(enabled[line.key]);
      let series = api.overlaySeries.get(line.key);

      if (!want) {
        if (series) {
          api.chart.removeSeries(series);
          api.overlaySeries.delete(line.key);
        }
        continue;
      }

      const points = alignOverlayPoints(seriesMap[line.key] ?? [], candleTimes);
      if (!series) {
        series = api.chart.addSeries(LineSeries, {
          color: line.color,
          lineWidth: 2,
          lineType: LineType.WithSteps,
          priceLineVisible: false,
          lastValueVisible: true,
          crosshairMarkerVisible: true,
          title: line.label,
        });
        api.overlaySeries.set(line.key, series);
      }
      series.setData(points);
    }
  }, []);

  const ensureFsaData = useCallback(() => {
    if (!ide) return Promise.resolve(null);
    if (fsaSeriesRef.current?.ide === ide && fsaSeriesRef.current?.series) {
      return Promise.resolve(fsaSeriesRef.current.series);
    }

    setFsaLoading(true);
    setFsaError('');
    return fetch(`/api/stock/${encodeURIComponent(ide)}/main-fsa/`)
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || 'main_FSA 加载失败');
        return payload;
      })
      .then((payload) => {
        const series = payload.series ?? {};
        fsaSeriesRef.current = { ide, series };
        return series;
      })
      .catch((err) => {
        setFsaError(err.message);
        fsaSeriesRef.current = null;
        throw err;
      })
      .finally(() => setFsaLoading(false));
  }, [ide]);

  const toggleOverlay = useCallback(
    (key) => {
      setOverlayEnabled((prev) => {
        const next = { ...prev, [key]: !prev[key] };
        overlayEnabledRef.current = next;
        return next;
      });

      ensureFsaData()
        .then(() => {
          // Defer so overlayEnabledRef is updated.
          requestAnimationFrame(() => syncOverlaySeries());
        })
        .catch(() => {});
    },
    [ensureFsaData, syncOverlaySeries],
  );

  useEffect(() => {
    setOverlayEnabled(emptyOverlayState());
    overlayEnabledRef.current = emptyOverlayState();
    fsaSeriesRef.current = null;
    swingMarkersRef.current = null;
    setSwingError('');
    setShowSwingMarkers(defaultShowSwingMarkers);
    showSwingMarkersRef.current = defaultShowSwingMarkers;
    setFsaError('');
    setContextMenu(null);
  }, [ide, defaultShowSwingMarkers]);

  useEffect(() => {
    const container = containerRef.current;
    const stage = stageRef.current;
    if (!container || !stage) return undefined;

    let cancelled = false;
    setLoading(true);
    setError('');
    setBarInfo(null);

    const timeAxisOptions = getTimeAxisChartOptions({
      formatCrosshairTime: (time) => formatDateWithChangeToNow(time, recordsRef.current),
    });

    const initialHeight = fillHeight
      ? Math.max(container.clientHeight || 0, 120)
      : effectiveHeight;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: initialHeight,
      layout: {
        background: { color: '#0b1220' },
        textColor: '#e5e7eb',
        panes: {
          enableResize: true,
          separatorColor: '#020617',
          separatorHoverColor: 'rgba(148, 163, 184, 0.28)',
        },
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        ...timeAxisOptions.crosshair,
      },
      localization: timeAxisOptions.localization,
      leftPriceScale: {
        visible: false,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: initialRightOffset(period),
        ...timeAxisOptions.timeScale,
      },
    });

    const useRawPrices = adjustment === 'none';
    const panes = chart.panes();
    if (panes[0]?.setStretchFactor) {
      panes[0].setStretchFactor(4);
    }

    const paneKindByIndex = { 0: 'main' };

    const measurePaneLayouts = () => {
      const stage = stageRef.current;
      if (!stage || cancelled) return;
      const stageRect = stage.getBoundingClientRect();
      const next = chart.panes().map((pane, index) => {
        const el = pane.getHTMLElement?.();
        const rect = el?.getBoundingClientRect?.();
        return {
          index,
          kind: paneKindByIndex[index] ?? `pane-${index}`,
          top: rect ? rect.top - stageRect.top : 0,
          height: rect ? rect.height : pane.getHeight?.() ?? 0,
        };
      });
      setPaneLayouts(next);
    };

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef5350',
      downColor: '#26a69a',
      borderUpColor: '#ef5350',
      borderDownColor: '#26a69a',
      wickUpColor: '#ef5350',
      wickDownColor: '#26a69a',
    });

    const maSeriesList = MA_CONFIGS.map((cfg) =>
      chart.addSeries(LineSeries, {
        color: cfg.color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }),
    );

    const bollSeries = {
      mid: null,
      upper: null,
      lower: null,
    };
    if (showIndicators && indicatorEnabled.boll) {
      bollSeries.mid = chart.addSeries(LineSeries, {
        color: INDICATOR_COLORS.bollMid,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      bollSeries.upper = chart.addSeries(LineSeries, {
        color: INDICATOR_COLORS.bollUpper,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      bollSeries.lower = chart.addSeries(LineSeries, {
        color: INDICATOR_COLORS.bollLower,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
    }

    // Leave bottom room for the overlay volume histogram (shares the main pane).
    chart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.2 },
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });

    const volumeMaSeriesList = VOLUME_MA_CONFIGS.map((cfg) =>
      chart.addSeries(LineSeries, {
        color: cfg.color,
        lineWidth: 1,
        priceScaleId: 'volume',
        priceFormat: { type: 'volume' },
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }),
    );

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    const indicatorSeries = {};
    const paneKinds = showIndicators ? paneIndicatorKinds(indicatorEnabled) : [];
    for (const kind of paneKinds) {
      const pane = chart.addPane(true);
      if (pane?.setStretchFactor) pane.setStretchFactor(1);
      const paneIndex = pane.paneIndex();
      paneKindByIndex[paneIndex] = kind;
      try {
        pane.priceScale('right').applyOptions({
          scaleMargins: { top: 0.12, bottom: 0.12 },
        });
      } catch {
        // pane price scale may not exist yet
      }

      if (kind === 'macd') {
        indicatorSeries.macdHist = chart.addSeries(
          HistogramSeries,
          { priceLineVisible: false, lastValueVisible: false },
          paneIndex,
        );
        indicatorSeries.macdDif = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.macdDif,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
        indicatorSeries.macdDea = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.macdDea,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
      } else if (kind === 'rsi') {
        indicatorSeries.rsi6 = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.rsi6,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
        indicatorSeries.rsi12 = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.rsi12,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
        indicatorSeries.rsi24 = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.rsi24,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
      } else if (kind === 'kdj') {
        indicatorSeries.kdjK = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.kdjK,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
        indicatorSeries.kdjD = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.kdjD,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
        indicatorSeries.kdjJ = chart.addSeries(
          LineSeries,
          {
            color: INDICATOR_COLORS.kdjJ,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
          },
          paneIndex,
        );
      }
    }

    chartApiRef.current = {
      chart,
      overlaySeries: new Map(),
      candleTimes: [],
      markersApi: createSeriesMarkers(candleSeries, []),
    };

    const focusBar = (index) => {
      const records = recordsRef.current;
      if (!records.length || index < 0 || index >= records.length) return;

      const record = records[index];
      focusedIndexRef.current = index;
      const indicatorRow = indicatorLookupRef.current.get(record.dt) ?? null;
      if (!cancelled) {
        setBarInfo(
          recordToBarInfo(
            record,
            index > 0 ? records[index - 1] : null,
            indicatorRow,
            records[records.length - 1],
          ),
        );
      }

      const close = displayClose(record, useRawPrices);
      if (close != null) {
        chart.setCrosshairPosition(close, record.dt, candleSeries);
      }

      const visible = chart.timeScale().getVisibleLogicalRange();
      if (visible && (index < visible.from || index > visible.to)) {
        const span = visible.to - visible.from;
        chart.timeScale().setVisibleLogicalRange({
          from: index - span + 4,
          to: index + 4,
        });
      }
    };

    const onCrosshairMove = (param) => {
      if (!param.time) return;
      const records = recordsRef.current;
      const idx = records.findIndex((row) => row.dt === param.time);
      if (idx >= 0) {
        focusedIndexRef.current = idx;
        const indicatorRow = indicatorLookupRef.current.get(records[idx].dt) ?? null;
        if (!cancelled) {
          setBarInfo(
            recordToBarInfo(
              records[idx],
              idx > 0 ? records[idx - 1] : null,
              indicatorRow,
              records[records.length - 1],
            ),
          );
        }
      }
    };

    const onKeyDown = (event) => {
      const records = recordsRef.current;
      if (!records.length) return;

      if (event.key === 'End' && event.ctrlKey) {
        event.preventDefault();
        focusBar(records.length - 1);
        return;
      }

      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        if (period !== 'daily') return;
        event.preventDefault();
        applyDailyZoom(chart.timeScale(), {
          centerIndex: focusedIndexRef.current,
          totalBars: records.length,
          zoomIn: event.key === 'ArrowUp',
        });
        return;
      }

      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();

      let nextIndex = focusedIndexRef.current;
      if (nextIndex < 0) {
        nextIndex = records.length - 1;
      } else if (event.key === 'ArrowLeft') {
        nextIndex = Math.max(0, nextIndex - 1);
      } else {
        nextIndex = Math.min(records.length - 1, nextIndex + 1);
      }
      focusBar(nextIndex);
    };

    const onContextMenu = (event) => {
      if (!showFsaContextMenu) return;
      event.preventDefault();
      const stage = stageRef.current;
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      setContextMenu({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });
    };

    chart.subscribeCrosshairMove(onCrosshairMove);
    stage.addEventListener('keydown', onKeyDown);
    const onPaneResizeEnd = () => requestAnimationFrame(measurePaneLayouts);
    stage.addEventListener('pointerup', onPaneResizeEnd);
    if (showFsaContextMenu) {
      stage.addEventListener('contextmenu', onContextMenu);
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const nextOptions = { width: entry.contentRect.width };
      if (fillHeight) {
        nextOptions.height = Math.max(entry.contentRect.height || 0, 120);
      }
      chart.applyOptions(nextOptions);
      requestAnimationFrame(measurePaneLayouts);
    });
    resizeObserver.observe(container);
    requestAnimationFrame(measurePaneLayouts);

    const params = new URLSearchParams({ period, adjustment });
    const kinds = activeIndicatorKinds.join(',');
    const fdkPromise = fetch(`/api/stock/${encodeURIComponent(ide)}/fdk/?${params}`).then(async (res) => {
      if (!res.ok) throw new Error('FDK 行情数据加载失败');
      return res.json();
    });
    const indicatorPromise =
      showIndicators && kinds
        ? fetch(
            `/api/stock/${encodeURIComponent(ide)}/indicators/?${params}&kinds=${encodeURIComponent(kinds)}`,
          ).then(async (res) => {
            if (!res.ok) {
              const payload = await res.json().catch(() => ({}));
              throw new Error(payload.error || '技术指标加载失败');
            }
            return res.json();
          })
        : Promise.resolve({ series: {} });

    Promise.all([fdkPromise, indicatorPromise])
      .then(([payload, indicatorPayload]) => {
        if (cancelled) return;
        const records = payload.data ?? [];
        recordsRef.current = records;

        const { candles, volumes } = toSeriesData(records, { useRaw: useRawPrices });
        candleSeries.setData(candles);
        volumeSeries.setData(volumes);

        MA_CONFIGS.forEach((cfg, index) => {
          maSeriesList[index].setData(calcMA(candles, cfg.period));
        });
        VOLUME_MA_CONFIGS.forEach((cfg, index) => {
          volumeMaSeriesList[index].setData(calcVolumeMA(volumes, cfg.period));
        });

        const vma5Points = calcVolumeMA(volumes, 5);
        const vma10Points = calcVolumeMA(volumes, 10);
        const vma5ByTime = new Map(vma5Points.map((p) => [p.time, p.value]));
        const vma10ByTime = new Map(vma10Points.map((p) => [p.time, p.value]));

        const series = indicatorPayload.series ?? {};
        indicatorLookupRef.current = buildIndicatorLookup(series);

        if (bollSeries.mid && series.boll) {
          bollSeries.mid.setData(series.boll.mid ?? []);
          bollSeries.upper.setData(series.boll.upper ?? []);
          bollSeries.lower.setData(series.boll.lower ?? []);
        }
        if (indicatorSeries.macdHist && series.macd) {
          indicatorSeries.macdHist.setData(withMacdColors(series.macd.hist));
          indicatorSeries.macdDif.setData(series.macd.dif ?? []);
          indicatorSeries.macdDea.setData(series.macd.dea ?? []);
        }
        if (indicatorSeries.rsi6 && series.rsi) {
          indicatorSeries.rsi6.setData(series.rsi.rsi_6 ?? []);
          indicatorSeries.rsi12.setData(series.rsi.rsi_12 ?? []);
          indicatorSeries.rsi24.setData(series.rsi.rsi_24 ?? []);
        }
        if (indicatorSeries.kdjK && series.kdj) {
          indicatorSeries.kdjK.setData(series.kdj.k ?? []);
          indicatorSeries.kdjD.setData(series.kdj.d ?? []);
          indicatorSeries.kdjJ.setData(series.kdj.j ?? []);
        }

        if (records.length) {
          const lastRec = records[records.length - 1];
          const prevRec = records.length > 1 ? records[records.length - 2] : null;
          const lastVol = useRawPrices
            ? pickNum(lastRec.raw_volume, lastRec.volume)
            : pickNum(lastRec.volume);
          const prevVol = prevRec
            ? useRawPrices
              ? pickNum(prevRec.raw_volume, prevRec.volume)
              : pickNum(prevRec.volume)
            : null;
          setStatusSnapshot({
            last: {
              ...(indicatorLookupRef.current.get(lastRec.dt) ?? {}),
              close: displayClose(lastRec, useRawPrices),
              volume: lastVol,
              vma5: vma5ByTime.get(lastRec.dt) ?? null,
              vma10: vma10ByTime.get(lastRec.dt) ?? null,
            },
            prev: prevRec
              ? {
                  ...(indicatorLookupRef.current.get(prevRec.dt) ?? {}),
                  close: displayClose(prevRec, useRawPrices),
                  volume: prevVol,
                  vma5: vma5ByTime.get(prevRec.dt) ?? null,
                  vma10: vma10ByTime.get(prevRec.dt) ?? null,
                }
              : null,
            changePct: calcChangePct(lastRec.raw_close, prevRec?.raw_close),
          });
        } else {
          setStatusSnapshot(null);
        }

        if (chartApiRef.current) {
          chartApiRef.current.candleTimes = candles.map((c) => c.time);
        }
        syncOverlaySeries();
        if (swingToggleVisible && showSwingMarkersRef.current) {
          ensureSwingData()
            .then(() => syncSwingMarkers())
            .catch(() => syncSwingMarkers());
        } else {
          syncSwingMarkers();
        }

        applyInitialVisibleRange(chart.timeScale(), candles.length, period);
        requestAnimationFrame(measurePaneLayouts);

        const visible = chart.timeScale().getVisibleLogicalRange();
        const lastIndex = candles.length - 1;
        const focusIndex = visible
          ? Math.min(lastIndex, Math.max(0, Math.floor(visible.to)))
          : lastIndex;
        focusBar(focusIndex);
        stage.focus({ preventScroll: true });
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      chart.unsubscribeCrosshairMove(onCrosshairMove);
      stage.removeEventListener('keydown', onKeyDown);
      stage.removeEventListener('pointerup', onPaneResizeEnd);
      if (showFsaContextMenu) {
        stage.removeEventListener('contextmenu', onContextMenu);
      }
      resizeObserver.disconnect();
      chart.remove();
      chartApiRef.current = null;
      recordsRef.current = [];
      indicatorLookupRef.current = new Map();
      focusedIndexRef.current = -1;
      setPaneLayouts([]);
      setStatusSnapshot(null);
    };
  }, [
    ide,
    fillHeight,
    layoutHeightKey,
    period,
    adjustment,
    syncOverlaySeries,
    syncSwingMarkers,
    ensureSwingData,
    swingToggleVisible,
    showFsaContextMenu,
    showIndicators,
    indicatorKindsKey,
    indicatorEnabled,
  ]);

  useEffect(() => {
    setPeriod(defaultPeriod);
  }, [ide, defaultPeriod]);

  useEffect(() => {
    if (!Object.values(overlayEnabled).some(Boolean)) return undefined;
    ensureFsaData()
      .then(() => syncOverlaySeries())
      .catch(() => {});
    return undefined;
  }, [overlayEnabled, ensureFsaData, syncOverlaySeries, period, ide]);

  useEffect(() => {
    if (!contextMenu) return undefined;
    const close = () => setContextMenu(null);
    const onKey = (event) => {
      if (event.key === 'Escape') close();
    };
    window.addEventListener('click', close);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('click', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [contextMenu]);

  const activeOverlays = FSA_OVERLAY_LINES.filter((line) => overlayEnabled[line.key]);

  const sizeStyle = fillHeight ? undefined : { minHeight: effectiveHeight };

  return (
    <div className={`stock-chart${fillHeight ? ' stock-chart--fill' : ''}`}>
      {showPeriodSelector ? (
        <div className="stock-chart__toolbar">
          <div className="stock-chart__toolbar-left">
            <Segmented
              size="small"
              value={period}
              onChange={setPeriod}
              options={periods}
            />
            {showIndicators ? (
              <div className="stock-chart__indicator-toggles">
                {INDICATOR_OPTIONS.map((opt) => (
                  <label key={opt.key} className="stock-chart__indicator-toggle">
                    <Checkbox
                      checked={Boolean(indicatorEnabled[opt.key])}
                      onChange={() => toggleIndicator(opt.key)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))}
                {swingToggleVisible ? (
                  <label className="stock-chart__indicator-toggle">
                    <Checkbox checked={showSwingMarkers} onChange={toggleSwingMarkers} />
                    <span>买卖点{swingLoading ? ' …' : ''}</span>
                  </label>
                ) : null}
              </div>
            ) : swingToggleVisible ? (
              <div className="stock-chart__indicator-toggles">
                <label className="stock-chart__indicator-toggle">
                  <Checkbox checked={showSwingMarkers} onChange={toggleSwingMarkers} />
                  <span>买卖点{swingLoading ? ' …' : ''}</span>
                </label>
              </div>
            ) : null}
          </div>
          <div className="stock-chart__legend">
            {MA_CONFIGS.map((cfg) => (
              <span key={cfg.label} className="stock-chart__legend-item">
                <i style={{ background: cfg.color }} />
                {cfg.label}
              </span>
            ))}
            {VOLUME_MA_CONFIGS.map((cfg) => (
              <span key={cfg.label} className="stock-chart__legend-item">
                <i style={{ background: cfg.color }} />
                {cfg.label}
              </span>
            ))}
            {activeOverlays.map((line) => (
              <span key={line.key} className="stock-chart__legend-item">
                <i style={{ background: line.color }} />
                {line.label}
              </span>
            ))}
            {showSwingMarkers && swingToggleVisible ? (
              <>
                <span className="stock-chart__legend-item">
                  <i style={{ background: SWING_BUY_COLOR }} />
                  买点
                </span>
                <span className="stock-chart__legend-item">
                  <i style={{ background: SWING_SELL_COLOR }} />
                  卖点
                </span>
              </>
            ) : null}          </div>
        </div>
      ) : showIndicators || swingToggleVisible ? (
        <div className="stock-chart__toolbar">
          <div className="stock-chart__indicator-toggles">
            {showIndicators
              ? INDICATOR_OPTIONS.map((opt) => (
                  <label key={opt.key} className="stock-chart__indicator-toggle">
                    <Checkbox
                      checked={Boolean(indicatorEnabled[opt.key])}
                      onChange={() => toggleIndicator(opt.key)}
                    />
                    <span>{opt.label}</span>
                  </label>
                ))
              : null}
            {swingToggleVisible ? (
              <label className="stock-chart__indicator-toggle">
                <Checkbox checked={showSwingMarkers} onChange={toggleSwingMarkers} />
                <span>买卖点{swingLoading ? ' …' : ''}</span>
              </label>
            ) : null}
          </div>
        </div>
      ) : null}
      {loading ? (
        <div className="stock-chart__loading">
          <Spin />
        </div>
      ) : null}
      {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 8 }} /> : null}
      {fsaError ? <Alert type="warning" message={fsaError} showIcon style={{ marginBottom: 8 }} /> : null}
      {swingError ? (
        <Alert type="warning" message={swingError} showIcon style={{ marginBottom: 8 }} />
      ) : null}
      <div
        ref={stageRef}
        className="stock-chart__stage"
        tabIndex={0}
        style={sizeStyle}
        onMouseDown={() => stageRef.current?.focus()}
      >
        <ChartPaneTooltips
          info={barInfo}
          indicatorEnabled={indicatorEnabled}
          paneLayouts={paneLayouts}
        />
        <StatusBadges badges={statusBadges} />
        <div
          ref={containerRef}
          className="stock-chart__container"
          style={sizeStyle}
        />
        {showFsaContextMenu && contextMenu ? (
          <div
            className="stock-chart__context-menu"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={(e) => e.stopPropagation()}
            onContextMenu={(e) => e.preventDefault()}
          >
            <div className="stock-chart__context-menu-title">
              财务线（季）{fsaLoading ? ' …' : ''}
            </div>
            {FSA_OVERLAY_LINES.map((line) => (
              <label key={line.key} className="stock-chart__context-menu-item">
                <Checkbox
                  checked={Boolean(overlayEnabled[line.key])}
                  onChange={() => toggleOverlay(line.key)}
                />
                <i style={{ background: line.color }} />
                <span>{line.label}</span>
              </label>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
