import { Routes, Route, Navigate } from 'react-router-dom';

import Home from './pages/Home';
import Bankuai from './pages/Bankuai';
import Industry from './pages/Industry';
import Pool from './pages/Pool';
import StockDetail from './pages/StockDetail';
import StockAnalysis from './pages/analysis/StockAnalysis';
import StockScreen from './pages/analysis/StockScreen';
import StockCompare from './pages/analysis/StockCompare';
import StockChannel from './pages/analysis/StockChannel';
import StockIndependentStrong from './pages/analysis/StockIndependentStrong';
import IndustryRelative from './pages/analysis/IndustryRelative';
import AiAdvice from './pages/analysis/AiAdvice';
import TechTabs from './pages/analysis/TechTabs';
import RatioAnalysis from './pages/analysis/RatioAnalysis';
import IndustryProfitGrowth from './pages/analysis/IndustryProfitGrowth';
import DataUpdate from './pages/DataUpdate';

export const menuRoutes = [
  {
    key: 'home',
    label: '首页',
    path: '/',
  },
  {
    key: 'bankuai',
    label: '板块',
    path: '/bankuai',
  },
  {
    key: 'pool',
    label: '股票池',
    path: '/pool',
  },
  {
    key: 'analysis',
    label: '分析',
    children: [
      // { key: 'stock', label: '股票信息', path: '/analysis/stock' },
      { key: 'screen', label: '股票筛选', path: '/analysis/screen' },
      { key: 'tech-tabs', label: '技术扫描综合', path: '/analysis/tech-tabs' },
      { key: 'compare', label: '股票对比', path: '/analysis/compare' },
      { key: 'ratio', label: '比率分析', path: '/analysis/ratio' },
      { key: 'industry-profit', label: '行业利润增长', path: '/analysis/industry-profit-growth' },
    ],
  },
  {
    key: 'data-update',
    label: '数据中心',
    path: '/data-update',
  },
];

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/bankuai" element={<Bankuai />} />
      <Route path="/industry/:name" element={<Industry />} />
      <Route path="/pool" element={<Pool />} />
      <Route path="/stock/:ide" element={<StockDetail />} />
      <Route path="/analysis/stock" element={<StockAnalysis />} />
      <Route path="/analysis/screen" element={<StockScreen />} />
      <Route path="/analysis/tech-tabs" element={<TechTabs />} />
      <Route path="/analysis/channel" element={<StockChannel />} />
      <Route path="/analysis/independent-strong" element={<StockIndependentStrong />} />
      <Route path="/analysis/industry-relative" element={<IndustryRelative />} />
      <Route path="/analysis/ai-advice" element={<AiAdvice />} />
      <Route path="/analysis/compare" element={<StockCompare />} />
      <Route path="/analysis/ratio" element={<RatioAnalysis />} />
      <Route path="/analysis/industry-profit-growth" element={<IndustryProfitGrowth />} />
      <Route path="/data-update" element={<DataUpdate />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
