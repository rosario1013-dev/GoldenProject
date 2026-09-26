import { Tabs } from 'antd';

import StockChannel from './StockChannel';
import StockIndependentStrong from './StockIndependentStrong';
import IndustryRelative from './IndustryRelative';
import AiAdvice from './AiAdvice';

export default function TechTabs() {
  return (
    <Tabs
      defaultActiveKey="channel"
      destroyInactiveTabPane={false}
      items={[
        {
          key: 'channel',
          label: '上升通道',
          children: <StockChannel />,
        },
        {
          key: 'independent-strong',
          label: '独立走强',
          children: <StockIndependentStrong />,
        },
        {
          key: 'industry-relative',
          label: '行业相关度',
          children: <IndustryRelative />,
        },
        {
          key: 'ai-advice',
          label: 'AI买入建议',
          children: <AiAdvice />,
        },
      ]}
    />
  );
}

