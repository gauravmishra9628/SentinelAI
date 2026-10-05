const alerts = [
  { id: 1, type: 'Collision warning', severity: 'Critical', region: 'Airport Road Junction' },
  { id: 2, type: 'Overspeeding', severity: 'High', region: 'NH-24 Highway' },
  { id: 3, type: 'Pedestrian risk', severity: 'Medium', region: 'Downtown School Zone' },
];

const AlertsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Recent alerts</h3>
      <ul className="alert-list">
        {alerts.map((alert) => (
          <li key={alert.id} className="alert-row">
            <div>
              <strong>{alert.type}</strong>
              <small>{alert.region}</small>
            </div>
            <span className={`badge ${alert.severity.toLowerCase()}`}>{alert.severity}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

export default AlertsPage;
