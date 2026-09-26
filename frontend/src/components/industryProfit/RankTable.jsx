import { Table, Tag } from 'antd';

import {
  formatAddedProfit,
  formatContribution,
  formatGrowthPct,
  formatProfit,
  formatScore,
  growthClassName,
  statusLabel,
} from '../../utils/industryProfitFormat';

export default function RankTable({ rows, loading, onSelect }) {
  const columns = [
    {
      title: 'Rank',
      dataIndex: 'rank',
      key: 'rank',
      width: 70,
      sorter: (a, b) => (a.rank ?? 0) - (b.rank ?? 0),
    },
    {
      title: 'Industry',
      dataIndex: 'industry',
      key: 'industry',
      width: 140,
      fixed: 'left',
      render: (value, row) => (
        <button type="button" className="ipg-link-btn" onClick={() => onSelect?.(row)}>
          {value}
          {row.low_sample_size ? <Tag style={{ marginLeft: 6 }}>小样本</Tag> : null}
        </button>
      ),
    },
    {
      title: 'Current Profit',
      dataIndex: 'current_profit',
      key: 'current_profit',
      width: 120,
      sorter: (a, b) => (a.current_profit ?? -Infinity) - (b.current_profit ?? -Infinity),
      render: (v) => formatProfit(v),
    },
    {
      title: 'YoY Growth',
      dataIndex: 'profit_growth_yoy',
      key: 'profit_growth_yoy',
      width: 120,
      sorter: (a, b) => (a.profit_growth_yoy ?? -Infinity) - (b.profit_growth_yoy ?? -Infinity),
      render: (v, row) =>
        v == null ? (
          <span className="rate-cell">{statusLabel(row.profit_status)}</span>
        ) : (
          <span className={growthClassName(v)}>{formatGrowthPct(v)}</span>
        ),
    },
    {
      title: '3Y CAGR',
      dataIndex: 'profit_cagr_3y',
      key: 'profit_cagr_3y',
      width: 110,
      sorter: (a, b) => (a.profit_cagr_3y ?? -Infinity) - (b.profit_cagr_3y ?? -Infinity),
      render: (v) => <span className={growthClassName(v)}>{formatGrowthPct(v)}</span>,
    },
    {
      title: '5Y CAGR',
      dataIndex: 'profit_cagr_5y',
      key: 'profit_cagr_5y',
      width: 110,
      sorter: (a, b) => (a.profit_cagr_5y ?? -Infinity) - (b.profit_cagr_5y ?? -Infinity),
      render: (v) => <span className={growthClassName(v)}>{formatGrowthPct(v)}</span>,
    },
    {
      title: 'Added Profit',
      dataIndex: 'added_profit',
      key: 'added_profit',
      width: 120,
      sorter: (a, b) => (a.added_profit ?? -Infinity) - (b.added_profit ?? -Infinity),
      render: (v) => <span className={growthClassName(v)}>{formatAddedProfit(v)}</span>,
    },
    {
      title: 'Contribution',
      dataIndex: 'profit_contribution',
      key: 'profit_contribution',
      width: 110,
      sorter: (a, b) =>
        (a.profit_contribution ?? -Infinity) - (b.profit_contribution ?? -Infinity),
      render: (v) => formatContribution(v),
    },
    {
      title: 'Stability',
      dataIndex: 'growth_stability_score',
      key: 'growth_stability_score',
      width: 100,
      sorter: (a, b) =>
        (a.growth_stability_score ?? -Infinity) - (b.growth_stability_score ?? -Infinity),
      render: (v) => formatScore(v),
    },
    {
      title: 'Growth Score',
      dataIndex: 'growth_score',
      key: 'growth_score',
      width: 120,
      sorter: (a, b) => (a.growth_score ?? -Infinity) - (b.growth_score ?? -Infinity),
      defaultSortOrder: 'descend',
      render: (v) => <strong className="ipg-score">{formatScore(v)}</strong>,
    },
    {
      title: 'Confidence',
      dataIndex: 'growth_confidence',
      key: 'growth_confidence',
      width: 110,
      sorter: (a, b) =>
        (a.growth_confidence ?? -Infinity) - (b.growth_confidence ?? -Infinity),
      render: (v) => formatScore(v),
    },
  ];

  return (
    <Table
      className="ipg-table"
      size="small"
      rowKey="industry"
      loading={loading}
      columns={columns}
      dataSource={rows || []}
      pagination={{ pageSize: 20, showSizeChanger: true }}
      scroll={{ x: 1300 }}
      onRow={(row) => ({
        onClick: () => onSelect?.(row),
        style: { cursor: 'pointer' },
      })}
    />
  );
}
