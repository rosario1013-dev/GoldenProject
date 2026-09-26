import { Tabs } from 'antd';

import CwTable from './CwTable';
import { PERIOD_MODES } from '../utils/cwColumns';

export default function EmbeddedFinanceTabs({ ide }) {
  const items = [
    {
      key: 'dashboard',
      label: '财务概览',
      children: (
        <CwTable
          ide={ide}
          fixedTable="dashboard"
          embedded
          defaultPeriodMode={PERIOD_MODES.QUARTER}
          nameColumnWidth={200}
          showControlsWhenEmbedded
        />
      ),
    },
    {
      key: 'reformed',
      label: '重构利润表',
      children: (
        <CwTable
          ide={ide}
          fixedTable="reformed"
          embedded
          defaultPeriodMode={PERIOD_MODES.QUARTER}
          nameColumnWidth={200}
          showControlsWhenEmbedded
        />
      ),
    },
  ];

  return <Tabs size="small" items={items} destroyInactiveTabPane style={{ marginTop: 12 }} />;
}
