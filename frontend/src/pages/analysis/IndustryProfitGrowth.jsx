import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Card,
  Col,
  Row,
  Select,
  Segmented,
  Space,
  Spin,
  Statistic,
  Typography,
} from 'antd';

import Top10Rank from '../../components/industryProfit/Top10Rank';
import GrowthScaleScatter from '../../components/industryProfit/GrowthScaleScatter';
import AddedProfitBars from '../../components/industryProfit/AddedProfitBars';
import ProfitTrendLines from '../../components/industryProfit/ProfitTrendLines';
import RankTable from '../../components/industryProfit/RankTable';
import GrowthValuationScatter from '../../components/industryProfit/GrowthValuationScatter';
import IndustryProfitDetail from '../../components/industryProfit/IndustryProfitDetail';
import {
  formatAddedProfit,
  formatProfit,
  periodLabel,
} from '../../utils/industryProfitFormat';

const { Title, Paragraph, Text } = Typography;

export default function IndustryProfitGrowth() {
  const [year, setYear] = useState(null);
  const [period, setPeriod] = useState('yoy');
  const [level, setLevel] = useState('1');
  const [industry, setIndustry] = useState(null);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const params = new URLSearchParams({ period, level });
        if (year != null) params.set('year', String(year));
        const res = await fetch(`/api/industry/profit-growth/?${params.toString()}`);
        const data = await res.json();
        if (cancelled) return;
        if (!res.ok && !data.industries?.length) {
          throw new Error(data.error || '加载失败');
        }
        setPayload(data);
        if (year == null && data.year != null) {
          setYear(data.year);
        }
        if (data.error && !data.industries?.length) {
          setError(data.error);
        }
      } catch (err) {
        if (!cancelled) {
          setPayload(null);
          setError(err.message || '加载失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [period, level, year]);

  const allIndustries = payload?.industries || [];
  const industries = useMemo(() => {
    if (!industry) return allIndustries;
    return allIndustries.filter((r) => r.industry === industry);
  }, [allIndustries, industry]);

  const top10Source = industry ? industries : payload?.top10 || [];
  const top10 = useMemo(() => {
    if (!industry) return top10Source;
    return industries.slice(0, 10).map((row, idx) => ({ ...row, rank: idx + 1 }));
  }, [industry, industries, top10Source]);

  const yearOptions = (payload?.years || []).map((y) => ({ value: y, label: String(y) }));
  const industryOptions = useMemo(
    () => allIndustries.map((r) => ({ value: r.industry, label: r.industry })),
    [allIndustries],
  );

  const onSelect = useCallback((row) => setSelected(row), []);

  return (
    <div className="ipg-page">
      <header className="ipg-page__header">
        <Title level={2} className="ipg-page__title">
          行业利润增长分析
        </Title>
        <Paragraph className="ipg-page__subtitle">
          发现利润增长最快的行业，分析行业盈利趋势和增长质量。
        </Paragraph>
      </header>

      <Card size="small" className="ipg-filters">
        <Space wrap size="middle">
          <Space size="small">
            <Text type="secondary">Year</Text>
            <Select
              style={{ width: 110 }}
              value={year}
              options={yearOptions}
              onChange={setYear}
              placeholder="Year"
            />
          </Space>
          <Space size="small">
            <Text type="secondary">Period</Text>
            <Segmented
              value={period}
              onChange={setPeriod}
              options={[
                { label: 'YoY', value: 'yoy' },
                { label: '3Y CAGR', value: '3y' },
                { label: '5Y CAGR', value: '5y' },
              ]}
            />
          </Space>
          <Space size="small">
            <Text type="secondary">Level</Text>
            <Segmented
              value={level}
              onChange={(next) => {
                setLevel(next);
                setIndustry(null);
              }}
              options={[
                { label: 'HY1', value: '1' },
                { label: 'HY2', value: '2' },
              ]}
            />
          </Space>
          <Space size="small">
            <Text type="secondary">Industry</Text>
            <Select
              allowClear
              showSearch
              style={{ minWidth: 180 }}
              value={industry || undefined}
              options={industryOptions}
              placeholder="All Industries"
              optionFilterProp="label"
              onChange={(v) => setIndustry(v || null)}
            />
          </Space>
          <Space size="small">
            <Text type="secondary">Market</Text>
            <Select
              style={{ width: 90 }}
              value="CN"
              options={[{ value: 'CN', label: 'CN' }]}
              disabled
            />
          </Space>
        </Space>
      </Card>

      {error ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 12 }}
          message={error}
          description="可在「数据中心」执行「行业利润预聚合」后刷新本页。"
        />
      ) : null}

      <Spin spinning={loading}>
        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col xs={24} md={8}>
            <Card size="small">
              <Statistic title="行业数" value={payload?.industry_count ?? 0} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small">
              <Statistic
                title="市场正向新增利润"
                value={formatAddedProfit(payload?.market_positive_added_profit)}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small">
              <Statistic
                title="市场净利润净变动"
                value={formatProfit(payload?.net_market_profit_change)}
              />
            </Card>
          </Col>
        </Row>

        <Card
          className="ipg-section"
          title={`利润增长最快行业 TOP 10 · ${periodLabel(period)}`}
          style={{ marginTop: 12 }}
        >
          <Top10Rank rows={top10} period={period} onSelect={onSelect} />
        </Card>

        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col xs={24} xl={12}>
            <Card className="ipg-section" title="利润增长 × 利润规模">
              <div className="ipg-chart-scroll">
                <GrowthScaleScatter rows={industries} period={period} onSelect={onSelect} />
              </div>
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card className="ipg-section" title="新增利润贡献度 TOP 10">
              <AddedProfitBars rows={industries} onSelect={onSelect} />
            </Card>
          </Col>
        </Row>

        <Card className="ipg-section" title="过去5年行业利润趋势（TOP 5）" style={{ marginTop: 12 }}>
          <ProfitTrendLines rows={top10} />
        </Card>

        <Card className="ipg-section" title="行业利润增长详细排名" style={{ marginTop: 12 }}>
          <RankTable rows={industries} loading={loading} onSelect={onSelect} />
        </Card>

        <Card className="ipg-section" title="行业增长 × 估值（预留）" style={{ marginTop: 12 }}>
          <GrowthValuationScatter rows={industries} onSelect={onSelect} />
        </Card>
      </Spin>

      <IndustryProfitDetail
        open={Boolean(selected)}
        row={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}
