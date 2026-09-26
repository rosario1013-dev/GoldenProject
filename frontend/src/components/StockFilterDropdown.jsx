import { Button, Checkbox, Dropdown } from 'antd';

import {
  ALL_STOCK_FILTERS,
  DEFAULT_STOCK_FILTERS,
  isAllFiltersEnabled,
  isAnyFilterEnabled,
} from '../utils/stockFilters';

const FILTER_OPTIONS = [
  { key: 'excludeChiNext', label: '过滤创业板（sz3）' },
  { key: 'excludeStar', label: '过滤科创板（sh68）' },
  { key: 'excludeBj', label: '过滤北证 A 股（bj）' },
  { key: 'excludeSt', label: '过滤 ST 股' },
];

export default function StockFilterDropdown({ filters, onChange, onToggleAll }) {
  const activeCount = FILTER_OPTIONS.filter((opt) => filters[opt.key]).length;

  const dropdownContent = (
    <div className="stock-filter-dropdown" onClick={(e) => e.stopPropagation()}>
      <Checkbox
        checked={isAllFiltersEnabled(filters)}
        indeterminate={isAnyFilterEnabled(filters) && !isAllFiltersEnabled(filters)}
        onChange={(e) => onToggleAll(e.target.checked)}
      >
        全部过滤
      </Checkbox>
      <div className="stock-filter-dropdown__divider" />
      {FILTER_OPTIONS.map((opt) => (
        <div key={opt.key} className="stock-filter-dropdown__item">
          <Checkbox
            checked={filters[opt.key]}
            onChange={(e) => onChange(opt.key, e.target.checked)}
          >
            {opt.label}
          </Checkbox>
        </div>
      ))}
    </div>
  );

  return (
    <Dropdown dropdownRender={() => dropdownContent} trigger={['click']}>
      <Button size="small">
        筛选{activeCount > 0 ? ` (${activeCount})` : ''}
      </Button>
    </Dropdown>
  );
}

export { ALL_STOCK_FILTERS, DEFAULT_STOCK_FILTERS };
