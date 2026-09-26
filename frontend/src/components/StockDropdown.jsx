import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Select, Spin } from 'antd';

function parsePathValue(pathname) {
  if (pathname.startsWith('/stock/')) {
    const ide = decodeURIComponent(pathname.slice('/stock/'.length));
    return ide ? `stock:${ide}` : undefined;
  }
  if (pathname.startsWith('/industry/')) {
    const name = decodeURIComponent(pathname.slice('/industry/'.length));
    return name ? `industry:${name}` : undefined;
  }
  return undefined;
}

export default function StockDropdown() {
  const navigate = useNavigate();
  const location = useLocation();
  const selectRef = useRef(null);
  const [stocks, setStocks] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key !== 'F10') return;
      event.preventDefault();
      selectRef.current?.focus();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const currentValue = useMemo(() => parsePathValue(location.pathname), [location.pathname]);

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetch('/api/stocks/').then((res) => (res.ok ? res.json() : { stocks: [] })),
      fetch('/api/hy/list/').then((res) => (res.ok ? res.json() : { sectors: [] })),
    ])
      .then(([stockData, hyData]) => {
        if (cancelled) return;
        setStocks(stockData.stocks ?? []);
        setIndustries(hyData.sectors ?? []);
      })
      .catch(() => {
        if (!cancelled) {
          setStocks([]);
          setIndustries([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo(
    () => [
      {
        label: '股票',
        options: stocks.map((stock) => ({
          value: `stock:${stock.ide}`,
          label: `${stock.name} ${stock.ABB} ${stock.ide}`,
          kind: 'stock',
          name: stock.name,
          ide: stock.ide,
          abb: stock.ABB,
        })),
      },
      {
        label: '行业',
        options: industries.map((sector) => ({
          value: `industry:${sector.name}`,
          label: `${sector.name} ${sector.ide} ${sector.code}`.trim(),
          kind: 'industry',
          name: sector.name,
          ide: sector.ide,
          code: sector.code,
        })),
      },
    ],
    [stocks, industries],
  );

  return (
    <Select
      ref={selectRef}
      className="stock-dropdown"
      style={{ width: 240 }}
      showSearch
      allowClear
      virtual
      value={currentValue}
      loading={loading}
      placeholder="搜索股票/行业"
      notFoundContent={loading ? <Spin size="small" /> : '暂无数据'}
      options={options}
      optionFilterProp="label"
      onChange={(value) => {
        if (!value) {
          navigate('/');
          return;
        }
        if (value.startsWith('stock:')) {
          navigate(`/stock/${value.slice('stock:'.length)}`);
          return;
        }
        if (value.startsWith('industry:')) {
          navigate(`/industry/${encodeURIComponent(value.slice('industry:'.length))}`);
        }
      }}
      onClear={() => navigate('/')}
      filterOption={(input, option) => {
        const keyword = input.trim().toLowerCase();
        if (!keyword) return true;
        const label = String(option?.label ?? '').toLowerCase();
        const name = String(option?.name ?? '').toLowerCase();
        const ide = String(option?.ide ?? '').toLowerCase();
        const abb = String(option?.abb ?? '').toLowerCase();
        const code = String(option?.code ?? '').toLowerCase();
        return (
          label.includes(keyword) ||
          name.includes(keyword) ||
          ide.includes(keyword) ||
          abb.includes(keyword) ||
          code.includes(keyword)
        );
      }}
    />
  );
}
