const securityStates = [
  { label: 'Perimeter', value: 'Protected' },
  { label: 'Access controls', value: 'Verified' },
  { label: 'Drone exclusions', value: '3 queued' },
  { label: 'Compliance', value: 'Nominal' },
];

const SecurityPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Security center</h3>
      <div className="metric-grid">
        {securityStates.map((state) => (
          <div key={state.label} className="metric-box green">
            <span>{state.label}</span>
            <strong>{state.value}</strong>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default SecurityPage;
