import { Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function StockAnalysis() {
  return (
    <div>
      <Title level={2}>股票信息</Title>
      <Paragraph>在此查看股票基本信息与分析数据。</Paragraph>
    </div>
  );
}
