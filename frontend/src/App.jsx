import { useCallback, useEffect, useState } from 'react';
import AIEngineStatus from './components/AIEngineStatus';
import Analytics from './components/Analytics';
import Header from './components/Header';
import LiveMonitoring from './components/LiveMonitoring';
import RecentAlerts from './components/RecentAlerts';
import RiskDetection from './components/RiskDetection';
import Sidebar from './components/Sidebar';
import StatCard from './components/StatCard';
import WelcomeSection from './components/WelcomeSection';
import { demoDashboardData } from './data/demoData';
import { getDashboard, getHealth } from './services/api';
import './App.css';

const App = () => {
  const [dashboardData, setDashboardData] = useState(demoDashboardData);
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [apiError, setApiError] = useState('');
  const [usingDemoData, setUsingDemoData] = useState(true);

  const loadDashboard = useCallback(async () => {
    setIsLoading(true);
    setApiError('');

    try {
      const [health, dashboard] = await Promise.all([getHealth(), getDashboard()]);
      setIsBackendOnline(health.status === 'ok');
      setDashboardData(dashboard);
      setUsingDemoData(false);
    } catch (error) {
      setIsBackendOnline(false);
      setDashboardData(demoDashboardData);
      setUsingDemoData(true);
      setApiError(error.message || 'Backend unavailable');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const interval = setInterval(loadDashboard, 30000);
    return () => clearInterval(interval);
  }, [loadDashboard]);

  return (
    <div className="app">
      <Sidebar />
      <main className="main-content">
        <Header
          alertCount={dashboardData.alerts.length}
          systemStatus={isBackendOnline}
        />

        <WelcomeSection
          isDemo={usingDemoData}
          onRetry={loadDashboard}
          systemStatus={isBackendOnline}
        />

        {(isLoading || apiError) && (
          <div className={`data-banner ${apiError ? 'warning' : 'loading'}`}>
            <span>{isLoading ? 'Loading live SentinelAI data...' : 'Backend unavailable. Showing clearly labeled demo data.'}</span>
            {apiError && <button onClick={loadDashboard}>Retry</button>}
          </div>
        )}

        <section className="dashboard-grid">
          <div className="stats-row">
            {dashboardData.statistics.map(stat => (
              <StatCard key={stat.title} {...stat} />
            ))}
          </div>

          <div className="primary-panels">
            <LiveMonitoring
              cameras={dashboardData.monitoring}
              isDemo={usingDemoData}
              isLoading={isLoading}
            />
            <RiskDetection
              events={dashboardData.risks}
              isDemo={usingDemoData}
              isLoading={isLoading}
            />
          </div>

          <div className="secondary-panels">
            <RecentAlerts
              alerts={dashboardData.alerts}
              isDemo={usingDemoData}
              isLoading={isLoading}
            />
            <Analytics
              analytics={dashboardData.analytics}
              isDemo={usingDemoData}
              isLoading={isLoading}
            />
            <AIEngineStatus
              engineData={dashboardData.aiEngineStatus}
              isDemo={usingDemoData}
              isLoading={isLoading}
            />
          </div>
        </section>
      </main>
    </div>
  );
};

export default App;
