import AIEngineStatus from '../components/AIEngineStatus';
import Analytics from '../components/Analytics';
import LiveMonitoring from '../components/LiveMonitoring';
import RecentAlerts from '../components/RecentAlerts';
import RiskDetection from '../components/RiskDetection';
import StatCard from '../components/StatCard';
import WelcomeSection from '../components/WelcomeSection';
import { demoDashboardData } from '../data/demoData';

const Dashboard = () => {
  const dashboardData = demoDashboardData;

  return (
    <>
      <WelcomeSection isDemo={true} onRetry={() => undefined} systemStatus={true} />
      <div className="data-banner loading">
        <span>Showing live-ready SentinelAI demo data</span>
      </div>

      <section className="dashboard-grid">
        <div className="stats-row">
          {dashboardData.statistics.map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        <div className="primary-panels">
          <LiveMonitoring cameras={dashboardData.monitoring} isDemo={true} isLoading={false} />
          <RiskDetection events={dashboardData.risks} isDemo={true} isLoading={false} />
        </div>

        <div className="secondary-panels">
          <RecentAlerts alerts={dashboardData.alerts} isDemo={true} isLoading={false} />
          <Analytics analytics={dashboardData.analytics} isDemo={true} isLoading={false} />
          <AIEngineStatus engineData={dashboardData.aiEngineStatus} isDemo={true} isLoading={false} />
        </div>
      </section>
    </>
  );
};

export default Dashboard;
