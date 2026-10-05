const settingGroups = [
  { title: 'Threat sensitivity', value: 'High' },
  { title: 'Incident escalation', value: 'Auto' },
  { title: 'Notifcations', value: 'Enabled' },
  { title: 'Analytic retention', value: '30 days' },
];

const SettingsPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>System settings</h3>
      <ul className="stack-list">
        {settingGroups.map((group) => (
          <li key={group.title}>
            <strong>{group.title}</strong>
            <span>{group.value}</span>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

export default SettingsPage;
