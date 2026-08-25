import './RecentAlerts.css';

const statusClass = status => `status-${String(status).toLowerCase()}`;
const severityClass = severity => `severity-${String(severity).toLowerCase()}`;

const RecentAlerts = ({ alerts = [], isDemo, isLoading }) => {
  return (
    <div className="alerts-panel">
      <div className="panel-header">
        <div>
          <h2>Recent Alerts</h2>
          <span className="panel-subtitle">{isDemo ? 'Demo alert feed' : 'Live alert feed'}</span>
        </div>
        {isLoading && <span className="panel-badge">SYNCING</span>}
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state">No recent alerts.</div>
      ) : (
        <div className="alerts-list">
          {alerts.map(alert => (
            <article key={alert.id} className="alert-item">
              <div className="alert-info">
                <div className="alert-type">{alert.type}</div>
                <div className="alert-meta">
                  <span>{alert.location}</span>
                  <span>{alert.timestamp}</span>
                </div>
              </div>
              <div className={`severity-badge ${severityClass(alert.severity)}`}>
                {alert.severity}
              </div>
              <div className={`status-badge ${statusClass(alert.status)}`}>
                {alert.status}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentAlerts;
