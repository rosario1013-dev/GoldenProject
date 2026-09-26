import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  FolderOpenOutlined,
  SyncOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const TASK_META = {
  quote: { label: '股价更新', color: 'blue' },
  cw: { label: '财务更新', color: 'green' },
  dividend: { label: '分红更新', color: 'orange' },
  stockinfo: { label: '公司信息', color: 'purple' },
  fsa: { label: '比率更新', color: 'cyan' },
  report: { label: '报告更新', color: 'magenta' },
  industry_profit: { label: '行业利润预聚合', color: 'geekblue' },
};

function CheckTag({ ok, label }) {
  return (
    <Tag icon={ok ? <CheckCircleOutlined /> : <CloseCircleOutlined />} color={ok ? 'success' : 'error'}>
      {label}
    </Tag>
  );
}

function formatResultValue(value) {
  if (value == null) return '-';
  if (typeof value === 'number') return value.toLocaleString('zh-CN');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function formatIsoLocal(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso;
  }
}

function formatDuration(startedAt, finishedAt) {
  if (!startedAt) return '—';
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return '—';
  const sec = Math.max(0, Math.round((end - start) / 1000));
  if (sec < 60) return `${sec} 秒`;
  const min = Math.floor(sec / 60);
  const rem = sec % 60;
  return rem ? `${min} 分 ${rem} 秒` : `${min} 分`;
}

function formatOptionsBrief(options) {
  if (!options || typeof options !== 'object') return '—';
  const parts = [];
  if (options.scope) parts.push(options.scope === 'recent' ? '增量' : '全量');
  if (options.recent_trading_days != null) parts.push(`${options.recent_trading_days} 交易日`);
  if (options.recent_quarters != null) parts.push(`${options.recent_quarters} 季度`);
  if (options.kind) parts.push(options.kind);
  if (options.begin_time || options.end_time) {
    parts.push(`${options.begin_time || '?'} ~ ${options.end_time || '?'}`);
  }
  if (options.download_pdf) parts.push('下载 PDF');
  return parts.length ? parts.join(' · ') : JSON.stringify(options);
}

function buildDefaultTaskOptions(tasks) {
  const defaults = {};
  for (const task of tasks) {
    if (task.options) {
      defaults[task.key] = { ...task.options };
    }
  }
  return defaults;
}

function JobStatusTag({ status }) {
  if (status === 'running') {
    return (
      <Tag icon={<SyncOutlined spin />} color="processing">
        运行中
      </Tag>
    );
  }
  if (status === 'completed') {
    return (
      <Tag icon={<CheckCircleOutlined />} color="success">
        成功
      </Tag>
    );
  }
  if (status === 'failed') {
    return (
      <Tag icon={<CloseCircleOutlined />} color="error">
        失败
      </Tag>
    );
  }
  return <Tag>{status || '—'}</Tag>;
}

function TaskRangeOptions({ task, value, onChange, disabled }) {
  if (!task.options) return null;

  const opts = value || task.options;
  const isRecent = opts.scope === 'recent';
  const hasScopes = Array.isArray(task.options.scopes) && task.options.scopes.length > 0;

  return (
    <Space direction="vertical" size="small" style={{ width: '100%' }}>
      {hasScopes ? (
        <Select
          size="small"
          value={opts.scope}
          disabled={disabled}
          options={task.options.scopes}
          onChange={(scope) => onChange({ ...opts, scope })}
          style={{ width: '100%' }}
        />
      ) : null}
      {isRecent && task.key === 'quote' ? (
        <Space size="small" wrap>
          <Text type="secondary">最近</Text>
          <InputNumber
            size="small"
            min={1}
            max={500}
            value={opts.recent_trading_days}
            disabled={disabled}
            onChange={(n) => onChange({ ...opts, recent_trading_days: n ?? 10 })}
          />
          <Text type="secondary">个交易日</Text>
        </Space>
      ) : null}
      {isRecent && task.key === 'cw' ? (
        <Space size="small" wrap>
          <Text type="secondary">最近</Text>
          <InputNumber
            size="small"
            min={1}
            max={80}
            value={opts.recent_quarters}
            disabled={disabled}
            onChange={(n) => onChange({ ...opts, recent_quarters: n ?? 3 })}
          />
          <Text type="secondary">个季度</Text>
        </Space>
      ) : null}
      {task.key === 'industry_profit' ? (
        <Text type="secondary">汇总 HY1 + HY2 年报归母净利润 → tdx.INDUSTRY_PROFIT_YEARLY</Text>
      ) : null}
    </Space>
  );
}

function ActiveJobPanel({ activeJob }) {
  if (!activeJob) {
    return (
      <Card title="实时任务" size="small" className="data-center__panel">
        <Text type="secondary">当前没有运行中的更新任务</Text>
      </Card>
    );
  }

  const label = TASK_META[activeJob.task]?.label || activeJob.task;
  const isRunning = activeJob.status === 'running';

  return (
    <Card title="实时任务" size="small" className="data-center__panel">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div className="data-center__active-head">
          <Text strong>{label}</Text>
          <JobStatusTag status={activeJob.status} />
        </div>
        {isRunning ? (
          <Progress percent={99} status="active" showInfo={false} strokeColor="#1677ff" />
        ) : null}
        <Descriptions size="small" column={1}>
          <Descriptions.Item label="开始">{formatIsoLocal(activeJob.started_at)}</Descriptions.Item>
          <Descriptions.Item label="耗时">
            {formatDuration(activeJob.started_at, activeJob.finished_at)}
          </Descriptions.Item>
          {activeJob.options ? (
            <Descriptions.Item label="参数">{formatOptionsBrief(activeJob.options)}</Descriptions.Item>
          ) : null}
        </Descriptions>
        {activeJob.error ? (
          <Alert type="error" showIcon message={activeJob.error} />
        ) : null}
        {activeJob.result_summary ? (
          <Text type="secondary">{activeJob.result_summary}</Text>
        ) : null}
        {activeJob.result && !activeJob.result_summary ? (
          <Descriptions size="small" column={1} bordered>
            {Object.entries(activeJob.result)
              .slice(0, 6)
              .map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {formatResultValue(value)}
                </Descriptions.Item>
              ))}
          </Descriptions>
        ) : null}
      </Space>
    </Card>
  );
}

function LastSuccessPanel({ lastSuccess }) {
  const entries = Object.entries(lastSuccess || {});
  return (
    <Card title="最近成功同步" size="small" className="data-center__panel">
      {entries.length === 0 ? (
        <Text type="secondary">暂无成功记录（本进程内）</Text>
      ) : (
        <Descriptions size="small" column={1}>
          {entries.map(([task, finishedAt]) => (
            <Descriptions.Item key={task} label={TASK_META[task]?.label || task}>
              {formatIsoLocal(finishedAt)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
    </Card>
  );
}

export default function DataUpdate() {
  const [config, setConfig] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [ratioInfo, setRatioInfo] = useState(null);
  const [reportInfo, setReportInfo] = useState(null);
  const [tdxPath, setTdxPath] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningTask, setRunningTask] = useState(null);
  const [activeJob, setActiveJob] = useState(null);
  const [jobHistory, setJobHistory] = useState([]);
  const [jobSummary, setJobSummary] = useState({ total: 0, completed: 0, running: 0, failed: 0 });
  const [lastSuccess, setLastSuccess] = useState({});
  const [taskOptions, setTaskOptions] = useState({});
  const [fsaOptions, setFsaOptions] = useState({ scope: 'recent', recent_quarters: 40 });
  const [reportOptions, setReportOptions] = useState({
    kind: 'all',
    download_pdf: false,
    max_pages: 20,
    begin_time: '2020-01-01',
    end_time: new Date().toISOString().slice(0, 10),
  });
  const pollRef = useRef(null);
  const historyPollRef = useRef(null);

  const loadConfig = useCallback(async () => {
    const res = await fetch('/api/update/config/');
    if (!res.ok) throw new Error('加载配置失败');
    const data = await res.json();
    setConfig(data);
    setTdxPath(data.tdx_path || data.default_tdx_path || 'C:\\zd_zsone');
    return data;
  }, []);

  const loadJobHistory = useCallback(async () => {
    const res = await fetch('/api/update/jobs/?limit=50');
    if (!res.ok) throw new Error('加载任务历史失败');
    const data = await res.json();
    setJobHistory(data.jobs ?? []);
    setJobSummary(data.summary ?? { total: 0, completed: 0, running: 0, failed: 0 });
    setLastSuccess(data.last_success ?? {});
    return data;
  }, []);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      loadConfig(),
      fetch('/api/update/tasks/').then((res) => res.json()),
      fetch('/api/update/ratios/').then((res) => res.json()),
      fetch('/api/update/reports/').then((res) => res.json()),
      loadJobHistory(),
    ])
      .then(([, tasksData, ratiosData, reportsData]) => {
        if (!cancelled) {
          const taskList = tasksData.tasks ?? [];
          setTasks(taskList);
          setTaskOptions(buildDefaultTaskOptions(taskList));
          setRatioInfo(ratiosData);
          if (ratiosData.options) {
            setFsaOptions({ ...ratiosData.options });
          }
          setReportInfo(reportsData);
          if (reportsData.options) {
            setReportOptions({
              kind: reportsData.options.kind ?? 'all',
              download_pdf: Boolean(reportsData.options.download_pdf),
              max_pages: reportsData.options.max_pages ?? 20,
              begin_time: reportsData.options.begin_time ?? '2020-01-01',
              end_time:
                reportsData.options.end_time ?? new Date().toISOString().slice(0, 10),
            });
          }
        }
      })
      .catch((err) => {
        if (!cancelled) message.error(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    historyPollRef.current = setInterval(() => {
      loadJobHistory().catch(() => {});
    }, 8000);

    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
      if (historyPollRef.current) clearInterval(historyPollRef.current);
    };
  }, [loadConfig, loadJobHistory]);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollJob = (jobId, taskKey) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/update/jobs/${jobId}/`);
        if (!res.ok) throw new Error('查询任务状态失败');
        const job = await res.json();
        setActiveJob(job);

        if (job.status === 'completed') {
          stopPolling();
          setRunningTask(null);
          message.success(`${TASK_META[taskKey]?.label || taskKey} 完成`);
          loadJobHistory().catch(() => {});
        } else if (job.status === 'failed') {
          stopPolling();
          setRunningTask(null);
          message.error(job.error || '更新失败');
          loadJobHistory().catch(() => {});
        }
      } catch (err) {
        stopPolling();
        setRunningTask(null);
        message.error(err.message);
      }
    }, 1500);
  };

  const startJob = async (taskKey, options = {}) => {
    setRunningTask(taskKey);
    setActiveJob(null);

    const res = await fetch('/api/update/run/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task: taskKey,
        tdx_path: tdxPath,
        options,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '启动更新失败');

    setActiveJob({ ...data, status: 'running', task: taskKey });
    pollJob(data.job_id, taskKey);
    loadJobHistory().catch(() => {});
    message.info(`已开始${TASK_META[taskKey]?.label || taskKey}`);
  };

  const handleSavePath = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/update/config/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tdx_path: tdxPath }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '保存失败');
      setConfig(data);
      message.success('通达信路径已保存');
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRunBasic = async (taskKey) => {
    if (taskKey !== 'industry_profit' && !config?.ready) {
      message.warning('请先设置有效的通达信数据目录');
      return;
    }

    try {
      const options = taskOptions[taskKey] || {};
      let payload = {};
      if (taskKey === 'industry_profit') {
        payload = { levels: options.levels || '1,2' };
      } else {
        payload = { scope: options.scope };
        if (options.scope === 'recent') {
          if (taskKey === 'quote') {
            payload.recent_trading_days = options.recent_trading_days ?? 10;
          }
          if (taskKey === 'cw') {
            payload.recent_quarters = options.recent_quarters ?? 3;
          }
        }
      }
      await startJob(taskKey, payload);
    } catch (err) {
      setRunningTask(null);
      message.error(err.message);
    }
  };

  const handleRunFsa = async () => {
    try {
      const payload = { scope: fsaOptions.scope };
      if (fsaOptions.scope === 'recent') {
        payload.recent_quarters = fsaOptions.recent_quarters ?? 40;
      }
      await startJob('fsa', payload);
    } catch (err) {
      setRunningTask(null);
      message.error(err.message);
    }
  };

  const handleRunReport = async () => {
    try {
      await startJob('report', {
        kind: reportOptions.kind || 'all',
        download_pdf: Boolean(reportOptions.download_pdf),
        max_pages: reportOptions.max_pages ?? 20,
        begin_time: reportOptions.begin_time || '2020-01-01',
        end_time: reportOptions.end_time || new Date().toISOString().slice(0, 10),
      });
    } catch (err) {
      setRunningTask(null);
      message.error(err.message);
    }
  };

  const ratioColumns = [
    { title: '字段', dataIndex: 'key', key: 'key', width: 160 },
    { title: '名称', dataIndex: 'label', key: 'label', width: 180 },
    { title: 'GP_FSA 账户', dataIndex: 'account', key: 'account', width: 180 },
    { title: '说明', dataIndex: 'description', key: 'description' },
  ];

  const historyColumns = [
    {
      title: '任务',
      dataIndex: 'task',
      key: 'task',
      width: 120,
      render: (task) => TASK_META[task]?.label || task,
    },
    {
      title: '参数',
      dataIndex: 'options',
      key: 'options',
      ellipsis: true,
      render: (opts) => formatOptionsBrief(opts),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => <JobStatusTag status={status} />,
    },
    {
      title: '开始',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 168,
      render: (v) => formatIsoLocal(v),
    },
    {
      title: '结束',
      dataIndex: 'finished_at',
      key: 'finished_at',
      width: 168,
      render: (v) => formatIsoLocal(v),
    },
    {
      title: '耗时',
      key: 'duration',
      width: 100,
      render: (_, row) => formatDuration(row.started_at, row.finished_at),
    },
    {
      title: '结果',
      dataIndex: 'result_summary',
      key: 'result_summary',
      ellipsis: true,
      render: (text, row) => text || row.error || '—',
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  const pathConfigCard = (
    <Card title="通达信数据目录" className="data-center__config" size="small">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            prefix={<FolderOpenOutlined />}
            value={tdxPath}
            onChange={(e) => setTdxPath(e.target.value)}
            placeholder="例如 C:\zd_zsone"
            onPressEnter={handleSavePath}
          />
          <Button type="primary" loading={saving} onClick={handleSavePath}>
            保存
          </Button>
        </Space.Compact>

        {config ? (
          <div>
            <Space wrap>
              <CheckTag ok={config.checks?.root} label="根目录" />
              <CheckTag ok={config.checks?.vipdoc} label="vipdoc" />
              <CheckTag ok={config.checks?.cw} label="财务 cw" />
              <CheckTag ok={config.checks?.gbbq} label="gbbq 分红" />
              {config.ready ? (
                <Tag color="processing">目录就绪</Tag>
              ) : (
                <Tag color="warning">目录不完整</Tag>
              )}
            </Space>
            {config.paths ? (
              <Descriptions size="small" column={1} style={{ marginTop: 12 }}>
                <Descriptions.Item label="MongoDB">
                  {config.mongo_db} @ {config.mongo_host}
                </Descriptions.Item>
                <Descriptions.Item label="vipdoc">{config.paths.vipdoc}</Descriptions.Item>
              </Descriptions>
            ) : null}
          </div>
        ) : null}

        {!config?.ready ? (
          <Alert
            type="warning"
            showIcon
            message="请确认通达信安装目录正确，且包含 vipdoc、cw、gbbq 等子路径后再执行更新。"
          />
        ) : null}
      </Space>
    </Card>
  );

  const taskCards = (
    <Row gutter={[12, 12]} className="data-center__task-row">
      {tasks.map((task) => {
        const meta = TASK_META[task.key] || { label: task.label, color: 'default' };
        const isRunning = runningTask === task.key;

        return (
          <Col key={task.key} xs={24} sm={12} xl={6}>
            <Card
              className="data-center__task-card"
              size="small"
              title={meta.label}
              extra={<Tag color={meta.color}>{task.key}</Tag>}
            >
              <Paragraph type="secondary" className="data-center__task-desc">
                {task.description}
              </Paragraph>
              <TaskRangeOptions
                task={task}
                value={taskOptions[task.key]}
                disabled={runningTask != null}
                onChange={(next) =>
                  setTaskOptions((prev) => ({
                    ...prev,
                    [task.key]: next,
                  }))
                }
              />
              <Button
                type="primary"
                block
                style={{ marginTop: 8 }}
                disabled={
                  (task.key !== 'industry_profit' && !config?.ready) ||
                  (runningTask != null && !isRunning)
                }
                loading={isRunning}
                icon={isRunning ? <SyncOutlined spin /> : undefined}
                onClick={() => handleRunBasic(task.key)}
              >
                {isRunning ? '更新中…' : '开始更新'}
              </Button>
            </Card>
          </Col>
        );
      })}
    </Row>
  );

  const ratioTab = (
    <>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="比率由 GP_FSA 根据 MongoDB 中的 CW 财务数据计算，写入 tdx.FSA。请先完成财务更新。"
      />
      <Card
        size="small"
        title="比率字段"
        extra={<Tag color="cyan">{ratioInfo?.target_collection || 'tdx.FSA'}</Tag>}
      >
        <Table
          size="small"
          rowKey="key"
          pagination={false}
          columns={ratioColumns}
          dataSource={ratioInfo?.ratios ?? []}
          scroll={{ x: 720 }}
        />
      </Card>
      <Card size="small" title="比率更新" style={{ marginTop: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Select
            value={fsaOptions.scope}
            disabled={runningTask != null}
            options={ratioInfo?.options?.scopes ?? []}
            onChange={(scope) => setFsaOptions((prev) => ({ ...prev, scope }))}
            style={{ width: 280 }}
          />
          {fsaOptions.scope === 'recent' ? (
            <Space wrap>
              <Text type="secondary">计算并上传最近</Text>
              <InputNumber
                min={1}
                max={120}
                value={fsaOptions.recent_quarters}
                disabled={runningTask != null}
                onChange={(n) =>
                  setFsaOptions((prev) => ({ ...prev, recent_quarters: n ?? 40 }))
                }
              />
              <Text type="secondary">个季度的比率</Text>
            </Space>
          ) : null}
          <Button
            type="primary"
            loading={runningTask === 'fsa'}
            disabled={runningTask != null && runningTask !== 'fsa'}
            icon={runningTask === 'fsa' ? <SyncOutlined spin /> : undefined}
            onClick={handleRunFsa}
          >
            {runningTask === 'fsa' ? '更新中…' : '开始比率更新'}
          </Button>
        </Space>
      </Card>
    </>
  );

  const reportTab = (
    <>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="从东方财富同步研报与定期报告元数据到 MongoDB。默认只入库信息；勾选后才会下载 PDF。"
      />
      <Card size="small" title="报告更新">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space wrap>
            <Text type="secondary">范围</Text>
            <Select
              value={reportOptions.kind}
              disabled={runningTask != null}
              options={reportInfo?.options?.kinds ?? []}
              onChange={(kind) => setReportOptions((prev) => ({ ...prev, kind }))}
              style={{ width: 320 }}
            />
          </Space>
          <Space wrap>
            <Text type="secondary">本地下载 PDF</Text>
            <Switch
              checked={Boolean(reportOptions.download_pdf)}
              disabled={runningTask != null}
              onChange={(download_pdf) => setReportOptions((prev) => ({ ...prev, download_pdf }))}
            />
          </Space>
          <Space wrap>
            <Text type="secondary">最多翻页</Text>
            <InputNumber
              min={1}
              max={500}
              value={reportOptions.max_pages}
              disabled={runningTask != null}
              onChange={(n) => setReportOptions((prev) => ({ ...prev, max_pages: n ?? 20 }))}
            />
          </Space>
          <Space wrap>
            <Text type="secondary">起始日</Text>
            <Input
              style={{ width: 160 }}
              value={reportOptions.begin_time}
              disabled={runningTask != null}
              onChange={(e) =>
                setReportOptions((prev) => ({ ...prev, begin_time: e.target.value }))
              }
              placeholder="YYYY-MM-DD"
            />
            <Text type="secondary">末日</Text>
            <Input
              style={{ width: 160 }}
              value={reportOptions.end_time}
              disabled={runningTask != null}
              onChange={(e) =>
                setReportOptions((prev) => ({ ...prev, end_time: e.target.value }))
              }
              placeholder="YYYY-MM-DD"
            />
          </Space>
          <Button
            type="primary"
            loading={runningTask === 'report'}
            disabled={runningTask != null && runningTask !== 'report'}
            icon={runningTask === 'report' ? <SyncOutlined spin /> : undefined}
            onClick={handleRunReport}
          >
            {runningTask === 'report' ? '更新中…' : '开始报告更新'}
          </Button>
        </Space>
      </Card>
    </>
  );

  return (
    <div className="data-center">
      <div className="data-center__header">
        <Title level={2} style={{ marginBottom: 4 }}>
          数据中心
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          从通达信本地目录、东方财富报告接口或 GP_FSA 计算结果更新 MongoDB。任务历史保存在当前后端进程内存中。
        </Paragraph>
      </div>

      <Row gutter={[12, 12]} className="data-center__stats">
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="任务总数" value={jobSummary.total} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="成功" value={jobSummary.completed} valueStyle={{ color: '#52c41a' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="运行中" value={jobSummary.running} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="失败" value={jobSummary.failed} valueStyle={{ color: '#ff4d4f' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="data-center__body">
        <Col xs={24} lg={16}>
          {pathConfigCard}
          <div style={{ marginTop: 16 }}>{taskCards}</div>
          <Card size="small" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
            <Tabs
              items={[
                { key: 'ratio', label: '比率更新', children: ratioTab },
                { key: 'report', label: '报告更新', children: reportTab },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <ActiveJobPanel activeJob={activeJob} />
          <div style={{ marginTop: 16 }}>
            <LastSuccessPanel lastSuccess={lastSuccess} />
          </div>
        </Col>
      </Row>

      <Card
        title="更新历史"
        size="small"
        className="data-center__history"
        extra={
          <Button size="small" onClick={() => loadJobHistory().catch((e) => message.error(e.message))}>
            刷新
          </Button>
        }
      >
        <Table
          size="small"
          rowKey="id"
          columns={historyColumns}
          dataSource={jobHistory}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
          scroll={{ x: 960 }}
        />
      </Card>
    </div>
  );
}
