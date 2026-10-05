const actions = [
  { title: 'Escalate hotspot', detail: 'Airport Road Junction • risk 91' },
  { title: 'Dispatch unit', detail: 'Patrol Team Alpha • ready in 3 min' },
  { title: 'Verify camera integrity', detail: '3 sensors with low signal quality' },
];

const AICopilotPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>AI copilot</h3>
      <div className="risk-list">
        {actions.map((action) => (
          <div key={action.title} className="risk-item">
            <div>
              <strong>{action.title}</strong>
              <small>{action.detail}</small>
            </div>
            <span className="badge high">Ready</span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export default AICopilotPage;
