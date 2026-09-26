import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Segmented, Space, Spin, Switch, Table, Tabs, Tooltip } from 'antd';

import {
  DEFAULT_VISIBLE_FROM_YEAR,
  PERIOD_MODES,
  calcYoYChange,
  filterColumnsByPeriod,
  formatColumnTitle,
  formatYoYChange,
  getPriorYearColumn,
  isYearEndColumn,
  resolveDisplayColumns,
  splitColumnsByYearCutoff,
} from '../utils/cwColumns';
import { formatFinance, formatFinanceRaw } from '../utils/formatFinance';
import { getRateClassName } from '../utils/rateStyle';

function renderCellValue(value, isPercent, { showYoY, values, column, allColumns }) {
  const display = formatFinance(value, { isPercent });
  const raw = formatFinanceRaw(value, { isPercent });

  let yoyEl = null;
  if (showYoY && values && column) {
    const priorCol = getPriorYearColumn(column, allColumns);
    if (priorCol) {
      const yoy = calcYoYChange(value, values[priorCol], isPercent);
      const yoyText = formatYoYChange(yoy, isPercent);
      if (yoyText) {
        yoyEl = (
          <div className={`cw-cell-yoy ${getRateClassName(yoy)}`}>
            {yoyText}
          </div>
        );
      }
    }
  }

  const content = (
    <div className="cw-cell">
      <div className="cw-cell-value">{display}</div>
      {yoyEl}
    </div>
  );

  if (!raw) return content;
  return <Tooltip title={raw}>{content}</Tooltip>;
}

export default function CwTable({
  ide,
  fixedTable = null,
  embedded = false,
  defaultPeriodMode = PERIOD_MODES.QUARTER,
  nameColumnWidth = 300,
  showControlsWhenEmbedded = false,
}) {
  const [tables, setTables] = useState([]);
  const [activeTable, setActiveTable] = useState(fixedTable || '');
  const [data, setData] = useState(null);
  const [loadingTables, setLoadingTables] = useState(!fixedTable);
  const [loadingData, setLoadingData] = useState(false);
  const [error, setError] = useState('');
  const [periodMode, setPeriodMode] = useState(defaultPeriodMode);
  const [showYoY, setShowYoY] = useState(true);
  const [showOlder, setShowOlder] = useState(false);

  useEffect(() => {
    if (fixedTable) {
      setActiveTable(fixedTable);
      setLoadingTables(false);
      setTables([]);
      setError('');
      return undefined;
    }

    let cancelled = false;
    setLoadingTables(true);
    setError('');
    setTables([]);
    setActiveTable('');
    setData(null);
    setShowOlder(false);

    fetch(`/api/stock/${encodeURIComponent(ide)}/cw/`)
      .then((res) => {
        if (!res.ok) throw new Error('财务表列表加载失败');
        return res.json();
      })
      .then((payload) => {
        if (cancelled) return;
        const nextTables = payload.tables ?? [];
        setTables(nextTables);
        if (nextTables.length) {
          setActiveTable(nextTables[0].key);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingTables(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide, fixedTable]);

  useEffect(() => {
    if (!activeTable) return undefined;

    let cancelled = false;
    setLoadingData(true);
    setError('');
    setData(null);
    setShowOlder(false);

    fetch(`/api/stock/${encodeURIComponent(ide)}/cw/${encodeURIComponent(activeTable)}/`)
      .then(async (res) => {
        if (!res.ok) {
          let message = '财务数据加载失败';
          try {
            const payload = await res.json();
            if (payload?.error) message = payload.error;
          } catch {
            // ignore non-JSON error bodies
          }
          throw new Error(message);
        }
        return res.json();
      })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingData(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide, activeTable]);

  const allColumns = data?.columns ?? [];

  const periodColumns = useMemo(
    () => filterColumnsByPeriod(allColumns, periodMode),
    [allColumns, periodMode],
  );

  const { recent: recentColumns, older: olderColumns } = useMemo(
    () => splitColumnsByYearCutoff(periodColumns),
    [periodColumns],
  );

  const visibleColumns = useMemo(
    () => resolveDisplayColumns(periodColumns, { showOlder }),
    [periodColumns, showOlder],
  );

  const columns = useMemo(() => {
    if (!visibleColumns.length) return [];

    return [
      {
        title: '项目',
        dataIndex: 'name',
        key: 'name',
        fixed: 'left',
        width: nameColumnWidth,
        render: (name, row) => (
          <span
            style={{
              display: 'inline-block',
              paddingLeft: row.level * 20,
              color: row.color || undefined,
            }}
          >
            {name}
          </span>
        ),
      },
      ...visibleColumns.map((col) => ({
        title: formatColumnTitle(col, periodMode),
        dataIndex: ['values', col],
        key: col,
        align: 'right',
        width: showYoY ? 130 : 120,
        onHeaderCell: () => ({
          className: isYearEndColumn(col) ? 'cw-col-yend' : undefined,
        }),
        onCell: () => ({
          className: isYearEndColumn(col) ? 'cw-col-yend' : undefined,
        }),
        render: (value, row) =>
          renderCellValue(value, row.is_percent, {
            showYoY,
            values: row.values,
            column: col,
            allColumns,
          }),
      })),
    ];
  }, [visibleColumns, periodMode, showYoY, allColumns, nameColumnWidth]);

  const tabItems = tables.map((table) => ({
    key: table.key,
    label: table.label,
  }));

  const tableContent = (
    <>
      {!fixedTable ? (
        <Tabs
          activeKey={activeTable}
          items={tabItems}
          onChange={setActiveTable}
          size="small"
          style={{ marginBottom: 12 }}
        />
      ) : null}
      {!embedded || showControlsWhenEmbedded ? (
        <Space wrap style={{ marginBottom: 12 }}>
          <Segmented
            value={periodMode}
            onChange={(value) => {
              setPeriodMode(value);
              setShowOlder(false);
            }}
            options={[
              { label: '按季度', value: PERIOD_MODES.QUARTER },
              { label: '按年度', value: PERIOD_MODES.YEAR },
            ]}
          />
          <Space size={4}>
            <Switch size="small" checked={showYoY} onChange={setShowYoY} />
            <span>同比分析</span>
          </Space>
          {olderColumns.length > 0 ? (
            <Button type="link" size="small" onClick={() => setShowOlder((v) => !v)}>
              {showOlder
                ? `收起 ${DEFAULT_VISIBLE_FROM_YEAR} 年以前`
                : `展开 ${DEFAULT_VISIBLE_FROM_YEAR} 年以前（${olderColumns.length} 期）`}
            </Button>
          ) : null}
        </Space>
      ) : null}
      <div className="cw-table-wrap">
        {loadingData ? (
          <div style={{ textAlign: 'center', padding: 32 }}>
            <Spin />
          </div>
        ) : (data?.columns?.length ?? 0) === 0 ? (
          <Alert type="info" message="暂无财务数据" showIcon />
        ) : recentColumns.length === 0 && !showOlder ? (
          <Alert type="info" message="当前周期模式下暂无数据" showIcon />
        ) : (
          <Table
            className="cw-table"
            columns={columns}
            dataSource={(data?.rows ?? []).map((row) => ({ ...row, key: row.id }))}
            pagination={false}
            scroll={{ x: 'max-content' }}
            size="small"
            bordered
          />
        )}
      </div>
    </>
  );

  if (loadingTables) {
    const loadingNode = (
      <div style={{ textAlign: 'center', padding: 32 }}>
        <Spin />
      </div>
    );
    if (embedded) return loadingNode;
    return (
      <Card title="财务报表" size="small" style={{ marginTop: 16 }}>
        {loadingNode}
      </Card>
    );
  }

  if (error && !data) {
    const errorNode = <Alert type="error" message={error} showIcon />;
    if (embedded) return errorNode;
    return (
      <Card title="财务报表" size="small" style={{ marginTop: 16 }}>
        {errorNode}
      </Card>
    );
  }

  if (!fixedTable && !tables.length) {
    const emptyNode = <Alert type="info" message="暂无财务表" showIcon />;
    if (embedded) return emptyNode;
    return (
      <Card title="财务报表" size="small" style={{ marginTop: 16 }}>
        {emptyNode}
      </Card>
    );
  }

  if (embedded) {
    return tableContent;
  }

  return (
    <Card title="财务报表" size="small" style={{ marginTop: 16 }}>
      {tableContent}
    </Card>
  );
}
