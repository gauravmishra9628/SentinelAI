const IncidentDetailsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Incident details</h3>
      <div className="risk-item">
        <div>
          <strong>INC-2041</strong>
          <small>Wrong-way vehicle detection • Airport Road Junction</small>
        </div>
        <span className="badge critical">Critical</span>
      </div>
      <ul className="stack-list">
        <li>Detected at 21:14 local time</li>
        <li>Camera confirmation: 3 sensors matched the trajectory pattern</li>
        <li>Response action: dispatch team dispatched and local signage alert triggered</li>
      </ul>
    </div>
  </div>
);

export default IncidentDetailsPage;
