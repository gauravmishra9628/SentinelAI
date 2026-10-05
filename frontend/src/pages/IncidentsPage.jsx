const incidents = [
  { id: 'INC-2041', title: 'Wrong-way vehicle detection', severity: 'Critical', status: 'Escalated' },
  { id: 'INC-2082', title: 'Traffic signal anomaly', severity: 'High', status: 'Reviewing' },
  { id: 'INC-2140', title: 'Crowd buildup near transit stop', severity: 'Medium', status: 'Monitoring' },
];

const IncidentsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Incident queue</h3>
      <ul className="alert-list">
        {incidents.map((incident) => (
          <li key={incident.id} className="alert-row">
            <div>
              <strong>{incident.title}</strong>
              <small>{incident.id}</small>
            </div>
            <span className={`badge ${incident.severity.toLowerCase()}`}>{incident.severity}</span>
            <span className="badge neutral">{incident.status}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

export default IncidentsPage;
