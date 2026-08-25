import './LiveMonitoring.css';

const riskClass = risk => `risk-${String(risk).toLowerCase()}`;
const statusClass = status => `status-${String(status).toLowerCase()}`;

const LiveMonitoring = ({ cameras = [], isDemo, isLoading }) => {
  return (
    <div className="monitoring-panel">
      <div className="panel-header">
        <div>
          <h2>Live Road Monitoring</h2>
          <span className="panel-subtitle">{isDemo ? 'Demo camera stream data' : 'Connected to backend API'}</span>
        </div>
        <div className="live-indicator">
          <span className="live-dot"></span>
          <span>{isLoading ? 'SYNCING' : 'LIVE'}</span>
        </div>
      </div>

      {cameras.length === 0 ? (
        <div className="empty-state">No active cameras available.</div>
      ) : (
        <div className="monitoring-content">
          {cameras.map(camera => (
            <article key={camera.id} className="camera-card">
              <div className="camera-visual">
                <div className="lane-lines"></div>
                <span>{camera.id}</span>
              </div>
              <div className="camera-info">
                <div className="info-row">
                  <span className="info-label">Location</span>
                  <span className="info-value">{camera.location}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Traffic</span>
                  <span className="info-value">{camera.trafficLevel}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Vehicles</span>
                  <span className="info-value">{camera.detectedVehicles}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Pedestrians</span>
                  <span className="info-value">{camera.detectedPedestrians}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Risk</span>
                  <span className={`risk-badge ${riskClass(camera.riskLevel)}`}>{camera.riskLevel}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status</span>
                  <span className={`status-pill ${statusClass(camera.status)}`}>{camera.status}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Last update</span>
                  <span className="info-value">{camera.lastUpdate}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default LiveMonitoring;
