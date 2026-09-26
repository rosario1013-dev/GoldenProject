import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';

import App from './App';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.darkAlgorithm,
          token: {
            colorPrimary: '#1677ff',
            colorBgContainer: '#111827',
            colorBgElevated: '#1a2332',
            colorBgLayout: '#0b1220',
            colorBorder: 'rgba(255,255,255,0.08)',
            colorText: '#d1d5db',
            colorTextHeading: '#e5e7eb',
            colorTextSecondary: '#9ca3af',
            colorTextTertiary: '#9ca3af',
            colorTextDescription: '#9ca3af',
            colorLink: '#60a5fa',
            colorLinkHover: '#93c5fd',
            controlItemBgActive: 'rgba(22,119,255,0.15)',
            controlItemBgHover: '#1a2332',
          },
          components: {
            Table: {
              headerBg: '#1a2332',
              headerColor: '#e5e7eb',
              headerSortActiveBg: '#243044',
              headerSortHoverBg: '#1f2937',
              bodySortBg: '#151d2e',
              rowHoverBg: '#1a2332',
              rowSelectedBg: 'rgba(22,119,255,0.15)',
              rowSelectedHoverBg: 'rgba(22,119,255,0.22)',
              borderColor: 'rgba(255,255,255,0.08)',
              headerSplitColor: 'rgba(255,255,255,0.08)',
              footerBg: '#111827',
              footerColor: '#d1d5db',
            },
          },
        }}
      >
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </StrictMode>,
);
