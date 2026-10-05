const responsePlan = [
  'Notify command desk for region-level escalation.',
  'Deploy nearest patrol group to verified risk corridor.',
  'Open emergency communications and verify camera coverage.',
  'Synchronize with dispatch systems and public safety contacts.',
];

const EmergencyResponsePage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Emergency response</h3>
      <ul className="stack-list">
        {responsePlan.map((step) => (
          <li key={step}><strong>{step}</strong></li>
        ))}
      </ul>
    </div>
  </div>
);

export default EmergencyResponsePage;
