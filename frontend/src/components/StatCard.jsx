import './StatCard.css';

const StatCard = ({ title, value, icon = 'STAT', trend = 'neutral', label, status }) => {
  const trendClass = `trend-${trend}`;
  const valueStr = typeof value === 'number' ? value.toLocaleString() : value;

  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <span className="stat-icon">{icon}</span>
        {status && <span className={`mini-status ${status.toLowerCase()}`}>{status}</span>}
      </div>
      <span className="stat-title">{title}</span>
      <div className="stat-card-value">{valueStr}</div>
      {label && <div className="stat-card-label">{label}</div>}
      <span className={`trend-badge ${trendClass}`}>
        {trend === 'up' ? 'UP' : trend === 'down' ? 'DOWN' : 'FLAT'}
      </span>
    </div>
  );
};

export default StatCard;
