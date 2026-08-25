import { useEffect, useState } from 'react';
import './Header.css';

const Header = ({ alertCount = 0, systemStatus }) => {
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }));
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const statusLabel = systemStatus === null
    ? 'Checking System'
    : systemStatus
      ? 'System Online'
      : 'Backend Offline';

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="page-title">Road Safety Dashboard</h1>
      </div>
      <div className="header-center">
        <div className={`system-status ${systemStatus ? 'online' : 'offline'}`}>
          <span className="status-dot"></span>
          <span className="status-text">{statusLabel}</span>
        </div>
      </div>
      <div className="header-right">
        <div className="notifications">
          <button className="notification-btn" aria-label="Notifications">
            <span aria-hidden="true">AL</span>
            <span className="notification-badge">{alertCount}</span>
          </button>
        </div>
        <div className="user-profile">
          <div className="user-avatar" aria-hidden="true">OP</div>
          <div className="user-info">
            <span className="user-name">Operator</span>
            <span className="user-role">Administrator</span>
          </div>
        </div>
        <div className="current-time">{currentTime}</div>
      </div>
    </header>
  );
};

export default Header;
