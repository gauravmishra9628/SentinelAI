const engineStats = [
  { label: 'Inference latency', value: '118ms' },
  { label: 'Model confidence', value: '96.2%' },
  { label: 'Active pipelines', value: '14' },
  { label: 'Alert precision', value: '93.8%' },
];

const AIEnginePage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>AI engine</h3>
      <div className="metric-grid">
        {engineStats.map((stat) => (
          <div key={stat.label} className="metric-box blue">
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default AIEnginePage;
