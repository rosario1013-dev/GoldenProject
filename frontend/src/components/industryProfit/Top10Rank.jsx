import { Link } from 'react-router-dom';
import { Tag, Typography } from 'antd';

import {
  formatGrowthPct,
  formatProfit,
  formatAddedProfit,
  formatContribution,
  growthClassName,
  growthMetricValue,
  statusLabel,
} from '../../utils/industryProfitFormat';

const { Text } = Typography;

export default function Top10Rank({ rows, period, onSelect }) {
  if (!rows?.length) {
    return <div className="ipg-empty">暂无排行数据</div>;
  }

  return (
    <ol className="ipg-top10">
      {rows.map((row) => {
        const growth = growthMetricValue(row, period);
        return (
          <li key={row.industry} className="ipg-top10__item">
            <button
              type="button"
              className="ipg-top10__btn"
              onClick={() => onSelect?.(row)}
            >
              <span className="ipg-top10__rank">{row.rank ?? '—'}</span>
              <span className="ipg-top10__main">
                <span className={`ipg-top10__growth ${growthClassName(growth)}`}>
                  {formatGrowthPct(growth)}
                </span>
                <span className="ipg-top10__name">{row.industry}</span>
                {row.low_sample_size ? (
                  <Tag className="ipg-top10__tag">小样本</Tag>
                ) : null}
                {growth == null && row.profit_status && row.profit_status !== 'PROFITABLE' ? (
                  <Text type="secondary" className="ipg-top10__status">
                    {statusLabel(row.profit_status)}
                  </Text>
                ) : null}
              </span>
              <span className="ipg-top10__meta">
                <span>利润 {formatProfit(row.current_profit)}</span>
                <span>新增 {formatAddedProfit(row.added_profit)}</span>
                <span>贡献 {formatContribution(row.profit_contribution)}</span>
                <span>公司 {row.company_count}</span>
              </span>
            </button>
            <Link
              className="ipg-top10__link"
              to={`/industry/${encodeURIComponent(row.industry)}`}
              onClick={(e) => e.stopPropagation()}
            >
              详情
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
