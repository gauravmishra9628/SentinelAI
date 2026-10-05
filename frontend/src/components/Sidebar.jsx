import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const navItems = [
  { icon: 'DB', label: 'Dashboard', path: '/' },
  { icon: 'CC', label: 'AI Command Center', path: '/command-center', highlight: true },
  { icon: 'LM', label: 'Live Monitoring', path: '/live-monitoring' },
  { icon: 'RD', label: 'Risk Detection', path: '/risk-detection' },
  { icon: 'AL', label: 'Alerts', path: '/alerts' },
  { icon: 'IN', label: 'Incidents', path: '/incidents' },
  { icon: 'INV', label: 'AI Investigation', path: '/investigation' },
  { icon: 'MP', label: 'Road Map', path: '/road-map' },
  { icon: 'CM', label: 'Cameras', path: '/cameras' },
  { icon: 'AN', label: 'Analytics', path: '/analytics' },
  { icon: 'PR', label: 'AI Prediction', path: '/ai-prediction' },
  { icon: 'AI', label: 'AI Engine', path: '/ai-engine' },
  { icon: 'CO', label: 'AI Copilot', path: '/ai-copilot' },
  { icon: 'RP', label: 'Reports', path: '/reports' },
  { icon: 'AS', label: 'AI Assistant', path: '/ai-assistant' },
  { icon: 'SE', label: 'Settings', path: '/settings' },
  { icon: 'SC', label: 'Security Center', path: '/security', highlight: true },
  { icon: 'ER', label: 'Emergency Response', path: '/emergency-response', highlight: true },
];

const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);

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
        {navItems.map((item) => (
          <div key={item.path} className={`nav-item${item.highlight ? ' nav-item--highlight' : ''}`}>
            <NavLink
              to={item.path}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'active' : ''}${item.highlight ? ' nav-link--highlight' : ''}`
              }
              end={item.path === '/'}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span className="nav-label">{item.label}</span>}
              {!isCollapsed && item.highlight && <span className="nav-pulse" aria-hidden="true">●</span>}
            </NavLink>
          </div>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
