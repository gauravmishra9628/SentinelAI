import './Analytics.css';

const Analytics = ({ analytics = { metrics: [], trends: [] }, isDemo, isLoading }) => {
  const { metrics, trends } = analytics;
  const maxIncidents = Math.max(...trends.map(point => point.incidents), 1);

  return (
    <div className="analytics-panel">
      <div className="panel-header">
        <div>
          <h2>Road Safety Analytics</h2>
          <span className="panel-subtitle">{isDemo ? 'Demo analytics' : 'Backend analytics'}</span>
        </div>
        {isLoading && <span className="panel-badge">SYNCING</span>}
      </div>

      {metrics.length === 0 ? (
        <div className="empty-state">No analytics available.</div>
      ) : (
        <>
          <div className="analytics-grid">
            {metrics.map(metric => (
              <div key={metric.label} className="metric-card">
                <div className="metric-header">
                  <span className="metric-label">{metric.label}</span>
                  <span className="metric-value">{metric.value}</span>
                </div>
                <div className="metric-progress">
                  <div
                    className={`metric-fill metric-${metric.tone}`}
                    style={{ width: `${metric.percent}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          <div className="trend-chart" aria-label="Risk trend chart">
            {trends.map(point => (
              <div key={point.label} className="trend-column">
                <div className="trend-bars">
                  <span
                    className="trend-bar incidents"
                    style={{ height: `${(point.incidents / maxIncidents) * 100}%` }}
                  ></span>
                  <span
                    className="trend-bar risk"
                    style={{ height: `${point.riskScore}%` }}
                  ></span>
                </div>
                <span className="trend-label">{point.label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default Analytics;
