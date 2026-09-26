import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, Input, message, Select, Space, Tag, Typography } from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';

const { Text } = Typography;

async function readJson(res) {
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(payload.error || '操作失败');
  }
  return payload;
}

export default function PoolCategoryControl({ ide, size = 'small', compact = false }) {
  const [loading, setLoading] = useState(false);
  const [membership, setMembership] = useState([]);
  const [allCategories, setAllCategories] = useState([]);
  const [picked, setPicked] = useState(undefined);
  const [creating, setCreating] = useState(false);
  const [newCategory, setNewCategory] = useState('');

  const load = useCallback(() => {
    if (!ide) return undefined;
    setLoading(true);
    return fetch(`/api/pool/stock/${encodeURIComponent(ide)}/`)
      .then(readJson)
      .then((payload) => {
        setMembership(payload.categories ?? []);
        setAllCategories(payload.all_categories ?? []);
      })
      .catch((err) => {
        message.error(err.message);
      })
      .finally(() => setLoading(false));
  }, [ide]);

  useEffect(() => {
    load();
  }, [load]);

  const unusedCategories = useMemo(
    () => allCategories.filter((name) => !membership.includes(name)),
    [allCategories, membership],
  );

  const handleAdd = async (category) => {
    const name = (category || picked || '').trim();
    if (!name || !ide) return;
    setLoading(true);
    try {
      const payload = await fetch(`/api/pool/stock/${encodeURIComponent(ide)}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: name }),
      }).then(readJson);
      setMembership(payload.categories ?? []);
      setAllCategories(payload.all_categories ?? []);
      setPicked(undefined);
      message.success(`已加入「${name}」`);
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (category) => {
    if (!ide || !category) return;
    setLoading(true);
    try {
      const payload = await fetch(`/api/pool/stock/${encodeURIComponent(ide)}/`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category }),
      }).then(readJson);
      setMembership(payload.categories ?? []);
      setAllCategories(payload.all_categories ?? []);
      message.success(`已从「${category}」移除`);
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAndAdd = async () => {
    const name = newCategory.trim();
    if (!name) return;
    setLoading(true);
    try {
      await fetch('/api/pool/categories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: name }),
      }).then(readJson);
      await handleAdd(name);
      setNewCategory('');
      setCreating(false);
    } catch (err) {
      message.error(err.message);
      setLoading(false);
    }
  };

  if (!ide) return null;

  return (
    <div className={`pool-category-control${compact ? ' pool-category-control--compact' : ''}`}>
      {!compact ? (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
          后选股分类
        </Text>
      ) : null}
      <Space wrap size={[6, 6]} style={{ marginBottom: 8 }}>
        {membership.length ? (
          membership.map((name) => (
            <Tag
              key={name}
              closable
              color="blue"
              onClose={(e) => {
                e.preventDefault();
                handleRemove(name);
              }}
            >
              {name}
            </Tag>
          ))
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            尚未加入股票池
          </Text>
        )}
      </Space>
      <Space wrap size="small">
        <Select
          size={size}
          style={{ minWidth: 140 }}
          placeholder="选择分类加入"
          value={picked}
          allowClear
          loading={loading}
          options={unusedCategories.map((name) => ({ value: name, label: name }))}
          onChange={setPicked}
          notFoundContent="暂无可用分类"
        />
        <Button
          size={size}
          type="primary"
          icon={<PlusOutlined />}
          loading={loading}
          disabled={!picked}
          onClick={() => handleAdd()}
        >
          加入
        </Button>
        <Button
          size={size}
          icon={<PlusOutlined />}
          onClick={() => setCreating((v) => !v)}
        >
          新建分类
        </Button>
      </Space>
      {creating ? (
        <Space.Compact style={{ display: 'flex', marginTop: 8, maxWidth: 320 }}>
          <Input
            size={size}
            placeholder="新分类名，如 候选股"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            onPressEnter={handleCreateAndAdd}
          />
          <Button size={size} type="primary" loading={loading} onClick={handleCreateAndAdd}>
            创建并加入
          </Button>
        </Space.Compact>
      ) : null}
    </div>
  );
}

export function PoolCategoryManager({ onChange }) {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newName, setNewName] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    return fetch('/api/pool/categories/')
      .then(readJson)
      .then((payload) => {
        setCategories(payload.categories ?? []);
        onChange?.(payload.categories ?? []);
      })
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  }, [onChange]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setLoading(true);
    try {
      await fetch('/api/pool/categories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: name }),
      }).then(readJson);
      setNewName('');
      await load();
      message.success(`已创建「${name}」`);
    } catch (err) {
      message.error(err.message);
      setLoading(false);
    }
  };

  const handleDelete = async (name) => {
    setLoading(true);
    try {
      await fetch(`/api/pool/categories/${encodeURIComponent(name)}/`, {
        method: 'DELETE',
      }).then(readJson);
      await load();
      message.success(`已删除「${name}」`);
    } catch (err) {
      message.error(err.message);
      setLoading(false);
    }
  };

  return (
    <Space wrap>
      <Space.Compact>
        <Input
          size="small"
          placeholder="新建分类"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onPressEnter={handleCreate}
          style={{ width: 140 }}
        />
        <Button size="small" type="primary" loading={loading} onClick={handleCreate}>
          创建
        </Button>
      </Space.Compact>
      {categories.map((name) => (
        <Tag
          key={name}
          closable
          closeIcon={<DeleteOutlined />}
          onClose={(e) => {
            e.preventDefault();
            handleDelete(name);
          }}
        >
          {name}
        </Tag>
      ))}
    </Space>
  );
}
