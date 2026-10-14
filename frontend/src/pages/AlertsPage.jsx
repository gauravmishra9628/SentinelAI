import { useCallback, useEffect, useState } from 'react';
import Header from '../components/Header';
import { acknowledgeAlert, getAlertList, resolveAlert } from '../services/api';
import { useWebSocket } from '../services/websocket';

const formatTime = (value) => value ? new Date(value).toLocaleString() : '—';

const AlertsPage = () => {
  const { connectionState, events } = useWebSocket(['alert', 'alert.created', 'incident.created']);
  const [data, setData] = useState({ alerts: [], total: 0, active: 0 });
  const [error, setError] = useState('');
  const load = useCallback(async () => { try { setData(await getAlertList({ limit: 100 })); setError(''); } catch (err) { setError(err.message || 'Unable to load alerts'); } }, []);
  useEffect(() => { load(); const timer = window.setInterval(load, 30000); return () => window.clearInterval(timer); }, [load]);
  useEffect(() => { if (events.get('alert')?.length || events.get('alert.created')?.length) load(); }, [events, load]);
  const action = async (fn, id) => { try { await fn(id); await load(); } catch (err) { setError(err.message || 'Alert update failed'); } };
  return <><Header systemStatus={connectionState === 'CONNECTED'} alertCount={data.active || 0} /><section className="page-section"><div className="page-header"><div><h1 className="page-title">Alerts</h1><p className="page-subtitle">Persisted road-safety alerts from the detection pipeline</p></div><span className="badge">{connectionState === 'CONNECTED' ? 'LIVE' : 'REST POLLING'}</span></div>{error && <div className="data-banner warning">{error}</div>}<div className="incidents-summary-grid"><div className="summary-card"><h3>Total</h3><p className="summary-value">{data.total || 0}</p></div><div className="summary-card"><h3>Active</h3><p className="summary-value">{data.active || 0}</p></div><div className="summary-card"><h3>Acknowledged</h3><p className="summary-value">{data.acknowledged || 0}</p></div></div><div className="panel-card"><h3>Recent alerts</h3>{!data.alerts?.length ? <p>No persisted alerts yet.</p> : <ul className="alert-list">{data.alerts.map((alert) => <li key={alert.id} className="alert-row"><div><strong>{alert.type || 'Road safety'}</strong><small>{alert.message || alert.location || 'Location unavailable'} · {formatTime(alert.timestamp)}</small><small>{alert.camera_id || 'Camera unavailable'} · Risk {alert.risk_score ?? '—'}</small></div><div><span className={`badge ${String(alert.severity || '').toLowerCase()}`}>{alert.severity}</span><small>{alert.status}</small>{alert.status === 'ACTIVE' && <button className="action-btn" onClick={() => action(acknowledgeAlert, alert.id)}>Acknowledge</button>}{alert.status !== 'RESOLVED' && <button className="action-btn action-btn--secondary" onClick={() => action(resolveAlert, alert.id)}>Resolve</button>}</div></li>)}</ul>}</div></section></>;
};
export default AlertsPage;
