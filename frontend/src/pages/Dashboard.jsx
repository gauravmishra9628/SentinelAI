import { useCallback, useEffect, useState } from 'react';
import AIEngineStatus from '../components/AIEngineStatus';
import Analytics from '../components/Analytics';
import LiveMonitoring from '../components/LiveMonitoring';
import RecentAlerts from '../components/RecentAlerts';
import RiskDetection from '../components/RiskDetection';
import StatCard from '../components/StatCard';
import WelcomeSection from '../components/WelcomeSection';
import { getDashboard } from '../services/api';
import { useWebSocket } from '../services/websocket';

const empty = { statistics: [], monitoring: [], risks: [], alerts: [], analytics: { metrics: [], trends: [] }, aiEngineStatus: {} };
const Dashboard = () => {
  const { connectionState, events } = useWebSocket(['alert', 'alert.created', 'incident', 'incident.created', 'risk_update', 'risk.updated']);
  const [data, setData] = useState(empty);
  const [error, setError] = useState('');
  const load = useCallback(async () => { try { setData(await getDashboard()); setError(''); } catch (err) { setError(err.message || 'Backend connection unavailable'); } }, []);
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => { if ([...events.values()].some((items) => items.length)) load(); }, [events, load]);
  const live = connectionState === 'CONNECTED';
  return <><WelcomeSection isDemo={data.aiEngineStatus?.demo_mode} onRetry={load} systemStatus={!error} /><div className="data-banner loading"><span>{error || (live ? 'LIVE · WebSocket connected' : 'REST POLLING · WebSocket unavailable')}</span></div><section className="dashboard-grid"><div className="stats-row">{data.statistics.map((stat) => <StatCard key={stat.title} {...stat} />)}</div><div className="primary-panels"><LiveMonitoring cameras={data.monitoring} isDemo={data.aiEngineStatus?.demo_mode} isLoading={false} /><RiskDetection events={data.risks} isDemo={data.aiEngineStatus?.demo_mode} isLoading={false} /></div><div className="secondary-panels"><RecentAlerts alerts={data.alerts} isDemo={data.aiEngineStatus?.demo_mode} isLoading={false} /><Analytics analytics={data.analytics} isDemo={data.aiEngineStatus?.demo_mode} isLoading={false} /><AIEngineStatus engineData={data.aiEngineStatus} isDemo={data.aiEngineStatus?.demo_mode} isLoading={false} /></div></section></>;
};
export default Dashboard;
