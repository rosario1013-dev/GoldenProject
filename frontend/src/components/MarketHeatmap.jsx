import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Checkbox, Empty, Radio, Segmented, Spin, Typography } from 'antd';
import * as echarts from 'echarts';

import { DEFAULT_STOCK_FILTERS, filterStocks } from '../utils/stockFilters';
import { CHART, SURFACE } from '../utils/theme';

const { Text } = Typography;

const CHG_OPTIONS = [
  { value: 'chg_1d', label: '1日' },
  { value: 'chg_3d', label: '3日' },
  { value: 'chg_5d', label: '5日' },
  { value: 'chg_1m', label: '1月' },
  { value: 'chg_1y', label: '1年' },
];

const VIEW_MODE_OPTIONS = [
  { value: 'hy1', label: '一级板块' },
  { value: 'hy2', label: '二级板块' },
  { value: 'full', label: '综合' },
];

const BOARD_FILTER_OPTIONS = [
  { key: 'excludeChiNext', label: '过滤创业板' },
  { key: 'excludeStar', label: '过滤科创板' },
  { key: 'excludeBj', label: '过滤北证' },
];

/* A-share convention: red = up, green = down — denser stops for smoother gradient */
const COLOR_STOPS = [
  { pct: -5, color: '#00e676' },
  { pct: -3, color: '#00c853' },
  { pct: -2, color: '#2e7d32' },
  { pct: -1, color: '#1b5e20' },
  { pct: -0.3, color: '#37474f' },
  { pct: 0, color: CHART.neutral },
  { pct: 0.3, color: '#6d4c41' },
  { pct: 1, color: '#b71c1c' },
  { pct: 2, color: '#d50000' },
  { pct: 3, color: '#ff1744' },
  { pct: 5, color: '#ff5252' },
];

const LEGEND_STOPS = [
  { pct: -5, color: '#00e676' },
  { pct: -2, color: '#2e7d32' },
  { pct: 0, color: CHART.neutral },
  { pct: 2, color: '#d50000' },
  { pct: 5, color: '#ff5252' },
];

function formatChg(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

function hexToRgb(hex) {
  const raw = hex.replace('#', '');
  const full = raw.length === 3
    ? raw.split('').map((c) => c + c).join('')
    : raw;
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  };
}

function rgbToHex({ r, g, b }) {
  const toHex = (n) => Math.round(n).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function chgToColor(chg) {
  if (chg == null || Number.isNaN(Number(chg))) return CHART.neutral;
  const value = Number(chg);
  if (value <= COLOR_STOPS[0].pct) return COLOR_STOPS[0].color;
  const last = COLOR_STOPS[COLOR_STOPS.length - 1];
  if (value >= last.pct) return last.color;

  for (let i = 0; i < COLOR_STOPS.length - 1; i += 1) {
    const left = COLOR_STOPS[i];
    const right = COLOR_STOPS[i + 1];
    if (value >= left.pct && value <= right.pct) {
      const span = right.pct - left.pct || 1;
      const t = (value - left.pct) / span;
      const a = hexToRgb(left.color);
      const b = hexToRgb(right.color);
      return rgbToHex({
        r: lerp(a.r, b.r, t),
        g: lerp(a.g, b.g, t),
        b: lerp(a.b, b.b, t),
      });
    }
  }
  return CHART.neutral;
}

function collectStockLeaves(node, out = []) {
  if (!node) return out;
  if (node.node_type === 'stock' && node.ide) {
    out.push(node);
    return out;
  }
  for (const child of node.children || []) {
    collectStockLeaves(child, out);
  }
  return out;
}

function filterTreeNode(node, allowedIdes) {
  if (!node) return null;
  if (node.node_type === 'stock') {
    return allowedIdes.has(node.ide) ? { ...node } : null;
  }
  const children = (node.children || [])
    .map((child) => filterTreeNode(child, allowedIdes))
    .filter(Boolean);
  if (!children.length) return null;
  const next = { ...node, children };
  next.value = children.reduce((sum, child) => sum + (Number(child.value) || 0), 0);
  // Re-roll chg fields as simple value-weighted average of children
  for (const key of ['chg_1d', 'chg_3d', 'chg_5d', 'chg_1m', 'chg_1y']) {
    let totalW = 0;
    let weighted = 0;
    for (const child of children) {
      const chg = child[key];
      const weight = Number(child.value) || 0;
      if (chg == null || weight <= 0) continue;
      totalW += weight;
      weighted += Number(chg) * weight;
    }
    next[key] = totalW > 0 ? Math.round((weighted / totalW) * 100) / 100 : null;
  }
  return next;
}

/** Collapse to L1 sectors as leaves (size/color from rolled metrics). */
function toLevel1View(tree) {
  if (!tree?.children?.length) return tree;
  return {
    ...tree,
    children: tree.children.map((l1) => ({
      ...l1,
      node_type: 'sector',
      children: undefined,
    })),
  };
}

/** Flatten L2 sectors as leaves (or L1-direct stocks skipped). */
function toLevel2View(tree) {
  if (!tree?.children?.length) return tree;
  const leaves = [];
  for (const l1 of tree.children) {
    const kids = l1.children || [];
    const hasSubSectors = kids.some((c) => c.node_type !== 'stock');
    if (!hasSubSectors) {
      // No L2: treat L1 itself as a leaf
      leaves.push({
        ...l1,
        node_type: 'sector',
        children: undefined,
      });
      continue;
    }
    for (const l2 of kids) {
      if (l2.node_type === 'stock') continue;
      leaves.push({
        ...l2,
        node_type: 'sector',
        children: undefined,
      });
    }
  }
  return { ...tree, children: leaves };
}

/** Find industry node by name in the full (filtered) tree. */
function findSectorNode(node, name) {
  if (!node || !name) return null;
  if (node.node_type !== 'stock' && node.name === name) return node;
  for (const child of node.children || []) {
    const found = findSectorNode(child, name);
    if (found) return found;
  }
  return null;
}

function toEchartsNode(node, chgField) {
  const chg = node[chgField];
  const displayName = node.name || node.ide || '';
  const isStock = node.node_type === 'stock';
  const hasChildren = Boolean(node.children?.length);
  const isLeaf = isStock || !hasChildren;
  const base = {
    name: displayName,
    value: Number(node.value) || 1,
    itemStyle: {
      color: chgToColor(chg),
      borderColor: SURFACE.elevated,
      borderWidth: isLeaf ? 1 : 2,
    },
    label: {
      show: isLeaf,
      formatter: () => `${displayName}\n${formatChg(chg)}`,
      color: '#fff',
      fontSize: 11,
    },
    upperLabel: {
      show: !isLeaf,
      formatter: () => displayName,
      color: '#fff',
      fontSize: 11,
    },
    ide: node.ide,
    nodeType: node.node_type,
    displayName,
  };

  if (hasChildren) {
    base.children = node.children.map((child) => toEchartsNode(child, chgField));
  }
  return base;
}

export default function MarketHeatmap({
  sector = null,
  title = '市场热力图',
  height = 520,
  showFilters = true,
  showViewModes = false,
  className = '',
}) {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chgField, setChgField] = useState('chg_1d');
  const [viewMode, setViewMode] = useState('full');
  const [drillSector, setDrillSector] = useState(null);
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);

  const loadHeatmap = useCallback(() => {
    setLoading(true);
    setError('');
    const params = new URLSearchParams();
    if (sector) params.set('sector', sector);
    const query = params.toString();
    return fetch(`/api/market/heatmap/${query ? `?${query}` : ''}`)
      .then((res) => {
        if (!res.ok) throw new Error('热力图数据加载失败');
        return res.json();
      })
      .then((payload) => {
        setTree(payload.tree || null);
      })
      .catch((err) => {
        setTree(null);
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [sector]);

  useEffect(() => {
    loadHeatmap();
  }, [loadHeatmap]);

  const filteredTree = useMemo(() => {
    if (!tree) return null;
    const leaves = collectStockLeaves(tree);
    const filtered = filterStocks(
      leaves.map((leaf) => ({ ide: leaf.ide, name: leaf.name })),
      stockFilters,
    );
    const allowedIdes = new Set(filtered.map((row) => row.ide));
    if (allowedIdes.size === leaves.length) return tree;
    return filterTreeNode(tree, allowedIdes);
  }, [tree, stockFilters]);

  const viewTree = useMemo(() => {
    if (!filteredTree) return null;

    if (drillSector) {
      const sectorNode = findSectorNode(filteredTree, drillSector);
      if (!sectorNode) return null;
      // Show this industry like the综合 heatmap (sub-industries → stocks, or stocks).
      return {
        name: drillSector,
        node_type: 'root',
        children: sectorNode.children?.length
          ? sectorNode.children
          : [{ ...sectorNode, children: undefined }],
      };
    }

    if (!showViewModes || viewMode === 'full') return filteredTree;
    if (viewMode === 'hy1') return toLevel1View(filteredTree);
    if (viewMode === 'hy2') return toLevel2View(filteredTree);
    return filteredTree;
  }, [filteredTree, showViewModes, viewMode, drillSector]);

  const chartData = useMemo(() => {
    if (!viewTree?.children?.length) return [];
    return viewTree.children.map((child) => toEchartsNode(child, chgField));
  }, [viewTree, chgField]);

  const stockCount = useMemo(() => {
    if (drillSector && viewTree) return collectStockLeaves(viewTree).length;
    return collectStockLeaves(filteredTree).length;
  }, [filteredTree, viewTree, drillSector]);

  const tileCount = useMemo(() => {
    if (!viewTree?.children) return 0;
    if (drillSector || viewMode === 'full' || !showViewModes) return stockCount;
    return viewTree.children.length;
  }, [viewTree, viewMode, showViewModes, stockCount, drillSector]);

  const isBoardOverview = showViewModes && !drillSector && (viewMode === 'hy1' || viewMode === 'hy2');
  const isStockHeatmap = Boolean(drillSector) || viewMode === 'full' || !showViewModes;

  useEffect(() => {
    if (!chartRef.current || !chartData.length) return undefined;

    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current);
    }
    const chart = chartInstanceRef.current;

    chart.setOption(
      {
        backgroundColor: CHART.heatmapBg,
        tooltip: { show: false },
        series: [
          {
            type: 'treemap',
            roam: true,
            nodeClick: false,
            animation: false,
            selectedMode: false,
            breadcrumb: {
              show: true,
              bottom: 6,
              itemStyle: { color: '#333', borderColor: '#555', textStyle: { color: '#ddd' } },
            },
            width: '100%',
            height: '92%',
            top: 8,
            left: 8,
            right: 8,
            label: { overflow: 'truncate' },
            upperLabel: {
              show: true,
              height: 22,
              color: '#fff',
              backgroundColor: 'rgba(0,0,0,0.35)',
              fontSize: 11,
            },
            emphasis: { disabled: true },
            levels: [
              {
                itemStyle: {
                  borderColor: '#222',
                  borderWidth: 2,
                  gapWidth: 2,
                },
                upperLabel: { show: isStockHeatmap },
                emphasis: { disabled: true },
              },
              {
                itemStyle: {
                  borderColor: '#333',
                  borderWidth: 1,
                  gapWidth: 1,
                },
                upperLabel: { show: true },
                emphasis: { disabled: true },
              },
              {
                itemStyle: {
                  borderColor: SURFACE.elevated,
                  borderWidth: 1,
                  gapWidth: 1,
                },
                label: { show: true },
                emphasis: { disabled: true },
              },
            ],
            data: chartData,
          },
        ],
      },
      true,
    );

    const onClick = (params) => {
      if (!isBoardOverview) return;
      const data = params?.data;
      if (data?.nodeType === 'sector' && data.displayName) {
        setDrillSector(data.displayName);
      }
    };

    const onDblClick = (params) => {
      const data = params?.data;
      if (!data) return;
      if (data.nodeType === 'stock' && data.ide) {
        window.open(`/stock/${data.ide}`, '_blank', 'noopener,noreferrer');
      }
    };

    const onContextMenu = (event) => {
      event?.preventDefault?.();
      if (event?.event?.preventDefault) event.event.preventDefault();
      if (drillSector) {
        setDrillSector(null);
      }
    };

    const onDomContextMenu = (event) => {
      event.preventDefault();
      if (drillSector) {
        setDrillSector(null);
      }
    };

    const onResize = () => chart.resize();
    const el = chartRef.current;

    chart.on('click', onClick);
    chart.on('dblclick', onDblClick);
    chart.getZr().on('contextmenu', onContextMenu);
    el?.addEventListener('contextmenu', onDomContextMenu);
    window.addEventListener('resize', onResize);

    return () => {
      chart.off('click', onClick);
      chart.off('dblclick', onDblClick);
      chart.getZr().off('contextmenu', onContextMenu);
      el?.removeEventListener('contextmenu', onDomContextMenu);
      window.removeEventListener('resize', onResize);
    };
  }, [chartData, isBoardOverview, isStockHeatmap, drillSector]);

  useEffect(
    () => () => {
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    },
    [],
  );

  const handleStockFilterChange = (key, checked) => {
    setStockFilters((prev) => ({ ...prev, [key]: checked }));
  };

  const handleViewModeChange = (mode) => {
    setViewMode(mode);
    setDrillSector(null);
  };

  const footerHint = (() => {
    if (drillSector) {
      return `共 ${stockCount} 只股票 · ${drillSector} · 右键返回 · 双击个股打开详情`;
    }
    if (isBoardOverview && viewMode === 'hy1') {
      return `共 ${tileCount} 个一级板块 · 单击进入该行业热力图`;
    }
    if (isBoardOverview && viewMode === 'hy2') {
      return `共 ${tileCount} 个二级板块 · 单击进入该行业热力图`;
    }
    return `共 ${stockCount} 只股票 · 面积按成交额 · 滚轮缩放 · 拖拽平移 · 双击个股打开详情`;
  })();

  const cardTitle = drillSector ? (
    <span className="market-heatmap-card__title">
      <Button
        type="link"
        size="small"
        className="market-heatmap-card__back"
        onClick={() => setDrillSector(null)}
      >
        ← 返回
      </Button>
      <span>
        {title}
        <Text type="secondary" style={{ marginLeft: 8, fontWeight: 400 }}>
          / {drillSector}
        </Text>
      </span>
    </span>
  ) : (
    title
  );

  return (
    <Card
      title={cardTitle}
      size="small"
      className={`market-heatmap-card ${className}`.trim()}
      extra={
        <div className="market-heatmap-card__toolbar">
          {showViewModes ? (
            <Radio.Group
              size="small"
              optionType="button"
              buttonStyle="solid"
              value={viewMode}
              options={VIEW_MODE_OPTIONS}
              onChange={(e) => handleViewModeChange(e.target.value)}
            />
          ) : null}
          {showFilters ? (
            <div className="market-heatmap-card__filters">
              {BOARD_FILTER_OPTIONS.map((opt) => (
                <Checkbox
                  key={opt.key}
                  checked={stockFilters[opt.key]}
                  onChange={(e) => handleStockFilterChange(opt.key, e.target.checked)}
                >
                  {opt.label}
                </Checkbox>
              ))}
            </div>
          ) : null}
          <Segmented
            size="small"
            value={chgField}
            options={CHG_OPTIONS}
            onChange={setChgField}
          />
        </div>
      }
    >
      {error ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error} />
      ) : loading ? (
        <div className="market-heatmap-card__center">
          <Spin />
        </div>
      ) : !chartData.length ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无热力图数据" />
      ) : (
        <>
          <div ref={chartRef} className="market-heatmap" style={{ height }} />
          <div className="market-heatmap-card__footer">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {footerHint}
            </Text>
            <div className="market-heatmap-legend" aria-hidden>
              {LEGEND_STOPS.map((stop) => (
                <span key={stop.pct} className="market-heatmap-legend__item">
                  <i style={{ background: stop.color }} />
                  {stop.pct > 0 ? '+' : ''}
                  {stop.pct}%
                </span>
              ))}
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
