const actions = [
  'Validate vehicle trajectory against nearby intersections.',
  'Review camera timestamps for signal synchronization drift.',
  'Cross-check dispatch response times and team availability.',
];

const InvestigationPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Investigation</h3>
      <ul className="stack-list">
        {actions.map((item) => (
          <li key={item}><strong>{item}</strong></li>
        ))}
      </ul>
    </div>
  </div>
);

export default InvestigationPage;
