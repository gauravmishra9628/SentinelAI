const metrics = [
  { label: 'Collision risk', value: '12%', tone: 'danger' },
  { label: 'Traffic density', value: '67%', tone: 'amber' },
  { label: 'Pedestrian exposure', value: '24%', tone: 'blue' },
  { label: 'Safety score', value: '94', tone: 'green' },
];

const AnalyticsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Analytics</h3>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className={`metric-box ${metric.tone}`}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default AnalyticsPage;
