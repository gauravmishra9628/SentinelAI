const cameras = [
  { id: 'CAM-101', location: 'North Junction', status: 'Live', health: '98%' },
  { id: 'CAM-204', location: 'Airport Road', status: 'Live', health: '94%' },
  { id: 'CAM-309', location: 'School Zone', status: 'Recording', health: '91%' },
  { id: 'CAM-412', location: 'Ring Road', status: 'Offline', health: '63%' },
];

const CamerasPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Camera network</h3>
      <div className="camera-grid">
        {cameras.map((camera) => (
          <div key={camera.id} className="camera-panel">
            <div className="camera-visual" />
            <div className="camera-meta">
              <strong>{camera.location}</strong>
              <span>{camera.id}</span>
            </div>
            <div className="camera-row">
              <span className={`badge ${camera.status.toLowerCase()}`}>{camera.status}</span>
              <span className="badge neutral">{camera.health}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default CamerasPage;
