import './RiskDetection.css';

const severityClass = severity => `sev-${String(severity).toLowerCase()}`;

const RiskDetection = ({ events = [], isDemo, isLoading }) => {
  const riskLevels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(label => ({
    label,
    count: events.filter(event => event.severity === label).length,
  }));

  return (
    <div className="risk-panel">
      <div className="panel-header">
        <div>
          <h2>AI Risk Detection</h2>
          <span className="panel-subtitle">{isDemo ? 'Demo detections' : 'Backend detections'}</span>
        </div>
        {isLoading && <span className="panel-badge">SYNCING</span>}
      </div>

      <div className="risk-levels">
        {riskLevels.map(level => (
          <div key={level.label} className={`risk-level-card ${severityClass(level.label)}`}>
            <span className="risk-level-label">{level.label}</span>
            <span className="risk-level-count">{level.count}</span>
          </div>
        ))}
      </div>

      <div className="risk-events">
        <h3>Recent Risk Events</h3>
        {events.length === 0 ? (
          <div className="empty-state">No AI risk events detected.</div>
        ) : (
          <div className="events-list">
            {events.map(event => (
              <article key={event.id} className="event-item">
                <div className="event-score">{event.riskScore}</div>
                <div className="event-body">
                  <div className="event-main">
                    <span className="event-type">{event.detectedIssue}</span>
                    <span className={`severity-badge ${severityClass(event.severity)}`}>
                      {event.severity}
                    </span>
                  </div>
                  <div className="event-meta">
                    <span>{event.camera}</span>
                    <span>{event.location}</span>
                    <span>{event.timestamp}</span>
                  </div>
                </div>
                <div className="event-confidence">
                  <span>{event.confidence}%</span>
                  <small>{event.status}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default RiskDetection;
