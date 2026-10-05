const predictions = [
  { label: 'High-risk corridor', value: '12:00–14:00', detail: 'Peak traffic + vulnerable crossings' },
  { label: 'Weather effect', value: 'Moderate', detail: 'Visibility conditions contribute to risk' },
  { label: 'Recommended action', value: 'Activate alerting', detail: 'Deploy patrol at School Zone' },
];

const PredictiveRiskPage = () => (
  <div className="page-content">
    <div className="panel-card">
      <h3>Predictive risk</h3>
      <ul className="stack-list">
        {predictions.map((item) => (
          <li key={item.label}>
            <strong>{item.label}</strong>
            <div>{item.value}</div>
            <small>{item.detail}</small>
          </li>
        ))}
      </ul>
    </div>
  </div>
);

export default PredictiveRiskPage;
