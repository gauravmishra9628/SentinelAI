import './AIEngineStatus.css';

const statusClass = status => String(status).toLowerCase();

const AIEngineStatus = ({ engineData, isDemo, isLoading }) => {
  if (!engineData) {
    return (
      <div className="ai-engine-panel">
        <div className="panel-header">
          <h2>AI Engine Status</h2>
        </div>
        <div className="empty-state">No engine status available.</div>
      </div>
    );
  }

  const statusItems = [
    { label: 'Model Status', value: engineData.modelStatus },
    { label: 'Inference Status', value: engineData.inferenceStatus },
    { label: 'Camera Processing', value: engineData.cameraProcessingStatus },
    { label: 'API Status', value: engineData.apiStatus },
    { label: 'Model Version', value: engineData.modelVersion },
    { label: 'Uptime', value: engineData.uptime },
  ];

  return (
    <div className="ai-engine-panel">
      <div className="panel-header">
        <div>
          <h2>AI Engine Status</h2>
          <span className="panel-subtitle">{isDemo ? 'Demo engine telemetry' : 'Backend engine telemetry'}</span>
        </div>
        <div className={`engine-status-indicator ${statusClass(engineData.status)}`}>
          <span className="status-dot"></span>
          <span>{isLoading ? 'SYNCING' : engineData.status}</span>
        </div>
      </div>

      <div className="engine-grid">
        {statusItems.map(item => (
          <div key={item.label} className="engine-item">
            <span className="engine-icon">{item.label.slice(0, 2).toUpperCase()}</span>
            <div className="engine-info">
              <span className="engine-label">{item.label}</span>
              <span className={`engine-value ${statusClass(item.value)}`}>{item.value}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="last-event">
        <span>Last processed event</span>
        <strong>{engineData.lastProcessedEvent}</strong>
      </div>
    </div>
  );
};

export default AIEngineStatus;
