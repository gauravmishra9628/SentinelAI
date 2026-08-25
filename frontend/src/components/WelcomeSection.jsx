import './WelcomeSection.css';

const WelcomeSection = ({ isDemo, onRetry, systemStatus }) => {
  const statusText = systemStatus
    ? 'Live monitoring connected'
    : 'Using demo monitoring data';

  return (
    <section className="welcome-section">
      <div className="welcome-content">
        <h1>Welcome to SentinelAI</h1>
        <p className="welcome-subtitle">
          AI-powered road safety monitoring for incidents, traffic risk, and accident prevention.
        </p>
        <div className="welcome-actions">
          <div className="system-status-indicator">
            <span className={`status-light ${systemStatus ? 'online' : 'offline'}`}></span>
            <span className="status-text">{statusText}</span>
          </div>
          {isDemo && <button onClick={onRetry}>Retry API</button>}
        </div>
      </div>
    </section>
  );
};

export default WelcomeSection;
