const cameras = [
  { id: 'CAM-001', camera: 'Main Highway', status: 'Online', risk: 'Low' },
  { id: 'CAM-014', camera: 'Airport Road', status: 'Monitoring', risk: 'High' },
  { id: 'CAM-022', camera: 'School Zone', status: 'Online', risk: 'Medium' },
  { id: 'CAM-117', camera: 'Ring Road', status: 'Offline', risk: 'Low' },
];

const LiveMonitoringPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Live camera grid</h3>
      <div className="camera-grid">
        {cameras.map((camera) => (
          <div key={camera.id} className="camera-panel">
            <div className="camera-visual" />
            <div className="camera-meta">
              <strong>{camera.camera}</strong>
              <span>{camera.id}</span>
            </div>
            <div className="camera-row">
              <span className={`badge ${camera.status.toLowerCase()}`}>{camera.status}</span>
              <span className={`badge risk-${camera.risk.toLowerCase()}`}>{camera.risk}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default LiveMonitoringPage;
