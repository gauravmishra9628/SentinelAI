const tiles = [
  { label: 'Operational load', value: '87%', tone: 'blue' },
  { label: 'Critical alerts', value: '3', tone: 'red' },
  { label: 'Incident queue', value: '14', tone: 'amber' },
  { label: 'Response SLA', value: '94%', tone: 'green' },
];

const actions = ['Clear congestion routes', 'Escalate wrong-way vehicle', 'Dispatch patrol team', 'Open evidence review'];

const CommandCenter = () => (
  <div className="page-content page-grid">
    <div className="panel-card large-card">
      <h3>Command center</h3>
      <p>Live system overview for road safety supervisors and dispatch teams.</p>
      <div className="metric-grid">
        {tiles.map((tile) => (
          <div key={tile.label} className={`metric-box ${tile.tone}`}>
            <span>{tile.label}</span>
            <strong>{tile.value}</strong>
          </div>
        ))}
      </div>
    </div>

    <div className="panel-card">
      <h3>Priority actions</h3>
      <ul className="stack-list">
        {actions.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>

    <div className="panel-card wide-card">
      <h3>Regional overview</h3>
      <div className="mini-chart">
        <span style={{ height: '28%' }} />
        <span style={{ height: '44%' }} />
        <span style={{ height: '62%' }} />
        <span style={{ height: '58%' }} />
        <span style={{ height: '72%' }} />
        <span style={{ height: '90%' }} />
        <span style={{ height: '64%' }} />
      </div>
    </div>
  </div>
);

export default CommandCenter;
