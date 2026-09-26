import { Layout } from 'antd';

import TopMenu from './components/menu';
import StockDropdown from './components/StockDropdown';
import { AppRoutes } from './route';
import './App.css';

const { Header, Content } = Layout;

export default function App() {
  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="app-logo">Project</div>
        <TopMenu />
        <StockDropdown />
      </Header>
      <Content className="app-content">
        <AppRoutes />
      </Content>
    </Layout>
  );
}
