import { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Empty, Segmented, Space, Spin, Table, Tag, Typography } from 'antd';

const { Text, Link: AntLink } = Typography;

function openPdf(row) {
  if (row?.pdf_url) {
    window.open(row.pdf_url, '_blank', 'noopener,noreferrer');
  }
}

export default function StockReports({ ide, embedded = false }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);
  const [kind, setKind] = useState('research');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setPayload(null);

    fetch(`/api/stock/${encodeURIComponent(ide)}/reports/`)
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '报告加载失败');
        return data;
      })
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '报告加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide]);

  const rows = useMemo(() => {
    if (!payload) return [];
    return kind === 'research' ? payload.research || [] : payload.filings || [];
  }, [payload, kind]);

  const researchColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 110,
    },
    {
      title: '类型',
      dataIndex: 'column_type',
      key: 'column_type',
      width: 100,
      render: (v) => (v ? <Tag>{v}</Tag> : '—'),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title, row) =>
        row.pdf_url ? (
          <AntLink onClick={() => openPdf(row)}>{title || row.id}</AntLink>
        ) : (
          title || '—'
        ),
    },
    {
      title: '机构',
      dataIndex: 'org',
      key: 'org',
      width: 120,
      ellipsis: true,
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
      width: 140,
      ellipsis: true,
    },
    {
      title: 'PDF',
      key: 'pdf',
      width: 90,
      render: (_, row) => (
        <Space size={4}>
          {row.pdf_url ? (
            <AntLink onClick={() => openPdf(row)}>在线</AntLink>
          ) : (
            <Text type="secondary">—</Text>
          )}
          {row.has_local ? <Tag color="green">本地</Tag> : null}
        </Space>
      ),
    },
  ];

  const filingColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      width: 110,
    },
    {
      title: '类型',
      dataIndex: 'column_name',
      key: 'column_name',
      width: 140,
      render: (v) => (v ? <Tag color="blue">{v}</Tag> : '—'),
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title, row) =>
        row.pdf_url ? (
          <AntLink onClick={() => openPdf(row)}>{title || row.id}</AntLink>
        ) : (
          title || '—'
        ),
    },
    {
      title: 'PDF',
      key: 'pdf',
      width: 90,
      render: (_, row) => (
        <Space size={4}>
          {row.pdf_url ? (
            <AntLink onClick={() => openPdf(row)}>在线</AntLink>
          ) : (
            <Text type="secondary">—</Text>
          )}
          {row.has_local ? <Tag color="green">本地</Tag> : null}
        </Space>
      ),
    },
  ];

  const kindSwitch = (
    <Segmented
      size="small"
      value={kind}
      onChange={setKind}
      options={[
        {
          label: `研报${payload ? ` (${payload.research_count ?? 0})` : ''}`,
          value: 'research',
        },
        {
          label: `定期报告${payload ? ` (${payload.filing_count ?? 0})` : ''}`,
          value: 'filings',
        },
      ]}
    />
  );

  const body = (
    <>
      {embedded ? <div style={{ marginBottom: 12 }}>{kindSwitch}</div> : null}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 32 }}>
          <Spin />
        </div>
      ) : null}
      {error ? <Alert type="error" message={error} showIcon /> : null}
      {!loading && !error ? (
        rows.length ? (
          <Table
            size="small"
            rowKey="id"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            columns={kind === 'research' ? researchColumns : filingColumns}
            dataSource={rows}
            scroll={{ x: kind === 'research' ? 800 : 640 }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              kind === 'research'
                ? '暂无该股研报（请先在资料更新中同步报告）'
                : '暂无年报/半年报/季报（请先在资料更新中同步报告）'
            }
          />
        )
      ) : null}
    </>
  );

  if (embedded) return body;

  return (
    <Card title="研究报告 / 定期报告" size="small" style={{ marginTop: 16 }} extra={kindSwitch}>
      {body}
    </Card>
  );
}
