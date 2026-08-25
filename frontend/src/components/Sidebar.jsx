import { useState } from 'react';
import './Sidebar.css';

const navItems = [
  { icon: 'DB', label: 'Dashboard', path: '/' },
  { icon: 'LM', label: 'Live Monitoring', path: '/live' },
  { icon: 'RD', label: 'Risk Detection', path: '/risk' },
  { icon: 'AL', label: 'Alerts', path: '/alerts' },
  { icon: 'AN', label: 'Analytics', path: '/analytics' },
  { icon: 'AI', label: 'AI Engine', path: '/ai' },
  { icon: 'SE', label: 'Settings', path: '/settings' },
];

const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activePath, setActivePath] = useState('/');

  return (
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon" aria-hidden="true">SI</span>
          {!isCollapsed && <span className="logo-text">SentinelAI</span>}
        </div>
        <button
          className="sidebar-toggle"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? '+' : '-'}
        </button>
      </div>
      <nav className="sidebar-nav" aria-label="Dashboard navigation">
        {navItems.map(item => (
          <div key={item.path} className="nav-item">
            <a
              href={item.path}
              className={`nav-link ${activePath === item.path ? 'active' : ''}`}
              onClick={event => {
                event.preventDefault();
                setActivePath(item.path);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span className="nav-label">{item.label}</span>}
            </a>
          </div>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
