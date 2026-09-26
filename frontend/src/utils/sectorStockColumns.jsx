import { useCallback, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, InputNumber, Popover } from 'antd';

import { formatPct, formatSignedPct, getRateClassName } from './rateStyle';

const CHG_COLUMNS = [
  { title: '一日涨幅', dataIndex: 'chg_1d', key: 'chg_1d' },
  { title: '三日涨幅', dataIndex: 'chg_3d', key: 'chg_3d' },
  { title: '五日涨幅', dataIndex: 'chg_5d', key: 'chg_5d' },
  { title: '一月涨幅', dataIndex: 'chg_1m', key: 'chg_1m' },
  { title: '一年涨幅', dataIndex: 'chg_1y', key: 'chg_1y' },
];

const FSA_COLUMNS = [
  { title: 'ROE', dataIndex: 'ROE', key: 'ROE', width: 72 },
  { title: 'ROA', dataIndex: 'ROA', key: 'ROA', width: 72 },
  { title: '净利同比1Y', dataIndex: '归母净利润同比_1Y', key: '归母净利润同比_1Y', width: 88 },
  { title: '净利同比', dataIndex: '归母净利润同比', key: '归母净利润同比', width: 80 },
  { title: '收入同比1Y', dataIndex: '营业总收入同比_1Y', key: '营业总收入同比_1Y', width: 88 },
  { title: '收入同比', dataIndex: '营业总收入同比', key: '营业总收入同比', width: 80 },
  { title: '毛利率', dataIndex: '毛利率', key: '毛利率', width: 72 },
  { title: '管理费用', dataIndex: '管理费用比例', key: '管理费用比例', width: 80 },
  { title: '销售费用', dataIndex: '销售费用比例', key: '销售费用比例', width: 80 },
  { title: '研发费用', dataIndex: '研发费用比例', key: '研发费用比例', width: 80 },
  { title: '营业成本', dataIndex: '营业成本比例', key: '营业成本比例', width: 80 },
];

function formatChg(value) {
  return formatSignedPct(value);
}

function toNumber(value) {
  if (value == null || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function compareNumbers(left, right) {
  return (toNumber(left) ?? -Infinity) - (toNumber(right) ?? -Infinity);
}

function encodeRange(range) {
  if (!range || (range.min == null && range.max == null)) return null;
  return `${range.min ?? ''}|${range.max ?? ''}`;
}

function decodeRange(value) {
  const [minRaw, maxRaw] = String(value ?? '').split('|');
  return { min: toNumber(minRaw), max: toNumber(maxRaw) };
}

function matchRange(raw, encoded) {
  const num = toNumber(raw);
  if (num == null) return false;
  const { min, max } = decodeRange(encoded);
  if (min != null && num < min) return false;
  if (max != null && num > max) return false;
  return true;
}

function RangeSortHeader({ title, align, sortOrder, range, onSort, onApplyRange, onClear }) {
  const [open, setOpen] = useState(false);
  const [min, setMin] = useState(range?.min ?? null);
  const [max, setMax] = useState(range?.max ?? null);
  const active = Boolean(sortOrder || range);

  const handleOpenChange = (next) => {
    if (next) {
      setMin(range?.min ?? null);
      setMax(range?.max ?? null);
    }
    setOpen(next);
  };

  const applyRange = () => {
    let lo = min;
    let hi = max;
    if (lo != null && hi != null && lo > hi) {
      [lo, hi] = [hi, lo];
    }
    onApplyRange(lo == null && hi == null ? null : { min: lo, max: hi });
    setOpen(false);
  };

  const clearAll = () => {
    setMin(null);
    setMax(null);
    onClear();
    setOpen(false);
  };

  return (
    <Popover
      trigger="click"
      open={open}
      onOpenChange={handleOpenChange}
      placement="bottomLeft"
      getPopupContainer={() => document.body}
      content={
        <div
          className="col-range-sort"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="col-range-sort__row">
            <Button
              size="small"
              type={sortOrder === 'ascend' ? 'primary' : 'default'}
              onClick={() => onSort(sortOrder === 'ascend' ? null : 'ascend')}
            >
              升序
            </Button>
            <Button
              size="small"
              type={sortOrder === 'descend' ? 'primary' : 'default'}
              onClick={() => onSort(sortOrder === 'descend' ? null : 'descend')}
            >
              降序
            </Button>
          </div>
          <div className="col-range-sort__row">
            <InputNumber size="small" placeholder="最小" value={min} onChange={setMin} />
            <span className="col-range-sort__sep">至</span>
            <InputNumber size="small" placeholder="最大" value={max} onChange={setMax} />
          </div>
          <div className="col-range-sort__row col-range-sort__row--end">
            <Button size="small" onClick={clearAll}>
              清除
            </Button>
            <Button size="small" type="primary" onClick={applyRange}>
              确定
            </Button>
          </div>
        </div>
      }
    >
      <button
        type="button"
        className={`col-range-sort__trigger${active ? ' is-active' : ''}`}
        style={{ justifyContent: align === 'center' ? 'center' : 'flex-end' }}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <span>{title}</span>
        {sortOrder === 'ascend' ? <span className="col-range-sort__mark">↑</span> : null}
        {sortOrder === 'descend' ? <span className="col-range-sort__mark">↓</span> : null}
        {range ? <span className="col-range-sort__dot" /> : null}
      </button>
    </Popover>
  );
}

function makeChgColumn({ title, dataIndex, key }) {
  return {
    title,
    dataIndex,
    key,
    width: 72,
    align: 'right',
    sorter: (a, b) => (a[dataIndex] ?? -Infinity) - (b[dataIndex] ?? -Infinity),
    render: (value) => <span className={getRateClassName(value)}>{formatChg(value)}</span>,
  };
}

function StockLink({ ide, children }) {
  if (!ide) return children ?? '—';
  return (
    <Link
      to={`/stock/${encodeURIComponent(ide)}`}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </Link>
  );
}

export function IndustryLink({ name, children }) {
  if (!name) return children ?? '—';
  return (
    <Link
      to={`/industry/${encodeURIComponent(name)}`}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </Link>
  );
}

export function buildSectorChgColumns() {
  return CHG_COLUMNS.map(makeChgColumn);
}

const IDENTITY_COLUMNS = [
  {
    title: '代码',
    dataIndex: 'ide',
    key: 'ide',
    width: 88,
    align: 'center',
    fixed: 'left',
    render: (ide) => <StockLink ide={ide}>{ide || '—'}</StockLink>,
  },
  {
    title: '名称',
    dataIndex: 'name',
    key: 'name',
    ellipsis: true,
    align: 'center',
    fixed: 'left',
    width: 88,
    render: (name, row) => <StockLink ide={row.ide}>{name || '—'}</StockLink>,
  },
];

export function useStockTableColumns({ defaultSort = null, onCriteriaChange } = {}) {
  const [sort, setSort] = useState(defaultSort);
  const [ranges, setRanges] = useState({});
  const onCriteriaChangeRef = useRef(onCriteriaChange);
  onCriteriaChangeRef.current = onCriteriaChange;

  const notify = useCallback(() => {
    onCriteriaChangeRef.current?.();
  }, []);

  const rangeSortColumn = useCallback(
    (spec) => {
      const key = spec.key;
      const { getValue: readValue, ...column } = spec;
      const getValue = readValue || ((row) => row?.[spec.dataIndex]);
      const range = ranges[key] ?? null;
      const sortOrder = sort?.key === key ? sort.order : null;
      const encoded = encodeRange(range);
      return {
        ...column,
        align: spec.align ?? 'right',
        showSorterTooltip: false,
        sorter: (a, b) => compareNumbers(getValue(a), getValue(b)),
        sortOrder,
        filteredValue: encoded ? [encoded] : null,
        onFilter: (value, record) => matchRange(getValue(record), value),
        onHeaderCell: () => ({ className: 'stock-col-range' }),
        title: (
          <RangeSortHeader
            title={spec.title}
            align={spec.align}
            sortOrder={sortOrder}
            range={range}
            onSort={(order) => {
              setSort(order ? { key, order } : null);
              notify();
            }}
            onApplyRange={(next) => {
              setRanges((prev) => {
                const updated = { ...prev };
                if (!next) delete updated[key];
                else updated[key] = next;
                return updated;
              });
              notify();
            }}
            onClear={() => {
              setRanges((prev) => {
                if (!(key in prev)) return prev;
                const updated = { ...prev };
                delete updated[key];
                return updated;
              });
              setSort((prev) => (prev?.key === key ? null : prev));
              notify();
            }}
          />
        ),
      };
    },
    [notify, ranges, sort],
  );

  const columns = useMemo(() => {
    const fsaColumns = FSA_COLUMNS.map((col) =>
      rangeSortColumn({
        ...col,
        render: (value) => <span className={getRateClassName(value)}>{formatPct(value)}</span>,
      }),
    );
    const chgColumns = CHG_COLUMNS.map((col) =>
      rangeSortColumn({
        ...col,
        width: 72,
        render: (value) => <span className={getRateClassName(value)}>{formatChg(value)}</span>,
      }),
    );
    return [...IDENTITY_COLUMNS, ...fsaColumns, ...chgColumns];
  }, [rangeSortColumn]);

  return { columns, rangeSortColumn };
}
