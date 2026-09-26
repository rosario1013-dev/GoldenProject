import { Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';

import { menuRoutes } from '../route';

function buildMenuItems(routes) {
  return routes.map((item) => {
    if (item.children) {
      return {
        key: item.key,
        label: item.label,
        children: item.children.map((child) => ({
          key: child.path,
          label: child.label,
        })),
      };
    }

    return {
      key: item.path,
      label: item.label,
    };
  });
}

export default function TopMenu() {
  const navigate = useNavigate();
  const location = useLocation();
  const menuItems = buildMenuItems(menuRoutes);

  return (
    <Menu
      mode="horizontal"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={({ key }) => navigate(key)}
      style={{ flex: 1, minWidth: 0, borderBottom: 'none' }}
    />
  );
}
