import { useCallback, useEffect, useState } from 'react';
import { getSecurityOverview, getSecurityAudit, getSecurityAlerts, getSecurityConfiguration, acknowledgeSecurityAlert, resolveSecurityAlert, applySecurityRetention, getStoredUser } from '../services/api';

const StatusBadge = ({ status }) => {
  const cls = String(status).toLowerCase();
  return <span className={`status-badge status-${cls}`}>{status}</span>;
};

const SeverityBadge = ({ severity }) => {
  const cls = String(severity).toLowerCase();
  return <span className={`severity-badge severity-${cls}`}>{severity}</span>;
};

const SecurityScore = ({ score, category, factors }) => (
  <div className="security-score">
    <div className="score-circle">
      <span className="score-value">{score}</span>
      <span className="score-label">/100</span>
    </div>
    <div className="score-details">
      <h3>Security Health Score</h3>
      <p className="score-category">{category}</p>
      {factors && factors.length > 0 && (
        <ul className="score-factors">
          {factors.map((f, i) => (
            <li key={i} className={f.delta < 0 ? 'negative' : 'positive'}>
              {f.delta > 0 ? '+' : ''}{f.delta} â€” {f.reason}
            </li>
          ))}
        </ul>
      )}
    </div>
  </div>
);

const ConfigurationStatus = ({ checks }) => (
  <div className="config-status">
    <h3>Security Configuration</h3>
    <div className="config-grid">
      {checks.map((c) => (
        <div key={c.key} className="config-item">
          <div>
            <strong>{c.label}</strong>
            <p>{c.description}</p>
          </div>
          <StatusBadge status={c.status === 'SECURE' ? 'ONLINE' : c.status} />
        </div>
      ))}
    </div>
  </div>
);

const AuditLog = ({ audit, onFilter }) => {
  const [filters, setFilters] = useState({ event_type: '', user_id: '', severity: '', status: '', search: '' });

  const handleChange = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onFilter(next);
  };

  return (
    <div className="audit-log">
      <div className="audit-header">
        <h3>Audit Log <small>{audit.total} events</small></h3>
        <button className="secondary-btn" onClick={() => { setFilters({ event_type: '', user_id: '', severity: '', status: '', search: '' }); onFilter({ limit: 50, offset: 0 }); }}>Clear Filters</button>
      </div>
      <div className="filter-bar">
        <input type="search" placeholder="Search..." value={filters.search} onChange={(e) => handleChange('search', e.target.value)} aria-label="Search audit" />
        <label><span>Event Type</span>
          <select value={filters.event_type} onChange={(e) => handleChange('event_type', e.target.value)}>
            <option value="">All</option>
            {['LOGIN','LOGOUT','LOGIN_FAILED','API_REQUEST','API_REQUEST_FAILED','CAMERA_VIEW','CAMERA_FULLSCREEN','CAMERA_DISCONNECT','CAMERA_RECONNECT','INCIDENT_VIEW','INCIDENT_ACK','INCIDENT_INVESTIGATE','INCIDENT_RESOLVE','EVIDENCE_VIEW','REPORT_GENERATED','AI_QUERY','SETTINGS_CHANGED'].map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label><span>User</span><input type="text" placeholder="User ID" value={filters.user_id} onChange={(e) => handleChange('user_id', e.target.value)} /></label>
        <label><span>Severity</span>
          <select value={filters.severity} onChange={(e) => handleChange('severity', e.target.value)}>
            <option value="">All</option>
            {['INFO','LOW','MEDIUM','HIGH','CRITICAL'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label><span>Status</span>
          <select value={filters.status} onChange={(e) => handleChange('status', e.target.value)}>
            <option value="">All</option>
            <option value="SUCCESS">Success</option>
            <option value="FAILED">Failed</option>
          </select>
        </label>
      </div>
      <div className="audit-table-wrap">
        <table className="audit-table">
          <thead><tr><th>Timestamp</th><th>Event</th><th>User</th><th>Resource</th><th>Action</th><th>Status</th></tr></thead>
          <tbody>
            {audit.events.map((e) => (
              <tr key={e.id}>
                <td>{new Date(e.timestamp).toLocaleString()}</td>
                <td><strong>{e.event_type}</strong></td>
                <td>{e.user_id || 'â€”'}</td>
                <td>{e.resource_id || e.resource_type || 'â€”'}</td>
                <td>{e.action || 'â€”'}</td>
                <td><StatusBadge status={e.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {audit.total > audit.events.length && <p className="audit-paginate">Showing {audit.events.length} of {audit.total} events.</p>}
    </div>
  );
};

const SecurityAlerts = ({ alertsData, onAcknowledge, onResolve }) => {
  const [filterStatus, setFilterStatus] = useState('ACTIVE');

  return (
    <div className="security-alerts">
      <h3>Security Alerts <small>{alertsData.total} total</small></h3>
      <div className="filter-bar">
        <label><span>Status</span>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </label>
      </div>
      {alertsData.alerts.length === 0 ? (
        <div className="empty-state">No alerts.</div>
      ) : (
        <ul className="alerts-list">
          {alertsData.alerts.map((a) => (
            <li key={a.id} className="alert-card">
              <div className="alert-card-main">
                <SeverityBadge severity={a.severity} />
                <strong>{a.reason}</strong>
                <span>{a.source}</span>
                <small>{new Date(a.timestamp).toLocaleString()}</small>
              </div>
              <div className="alert-card-status">
                <StatusBadge status={a.status} />
                {(a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED') && (
                  <div className="alert-actions">
                    {a.status === 'ACTIVE' && <button className="secondary-btn" onClick={() => onAcknowledge(a.id)}>Acknowledge</button>}
                    {a.status !== 'RESOLVED' && <button className="primary-btn" onClick={() => onResolve(a.id)}>Resolve</button>}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const SecurityTimeline = ({ events }) => (
  <div className="security-timeline">
    <h3>Security Event Timeline</h3>
    {events.length === 0 ? (
      <div className="empty-state">No timeline events yet.</div>
    ) : (
      <ul className="timeline-list">
        {events.map((e) => (
          <li key={e.id} className="timeline-item">
            <span className="timeline-time">{new Date(e.timestamp).toLocaleString()}</span>
            <span className="timeline-event">{e.event_type}</span>
            <span>{e.user_id || 'system'}</span>
            <span>{e.action || ''}</span>
            <StatusBadge status={e.status} />
          </li>
        ))}
      </ul>
    )}
  </div>
);

const AuditTrail = ({ trail }) => (
  <div className="audit-trail">
    <h3>Incident Audit Trail</h3>
    {trail.length === 0 ? (
      <div className="empty-state">No trail events yet.</div>
    ) : (
      <ul className="trail-list">
        {trail.map((t, i) => (
          <li key={i} className="trail-item">
            <span className="trail-step">{i + 1}</span>
            <span>{t.action}</span>
            <small>{new Date(t.timestamp).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    )}
  </div>
);

const SecurityPage = () => {
  const [overview, setOverview] = useState(null);
  const [audit, setAudit] = useState({ events: [], count: 0, total: 0, limit: 50, offset: 0, stats: {} });
  const [alertsData, setAlertsData] = useState({ alerts: [], total: 0 });
  const [config, setConfig] = useState({ checks: [] });
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState('');
  const [auditFilter, setAuditFilter] = useState({ limit: 50, offset: 0 });

  const loadData = useCallback(async () => {
    setLoading(true);
    setApiError('');
    try {
      const [ov, aud, al, cfg] = await Promise.all([
        getSecurityOverview().catch(() => null),
        getSecurityAudit(auditFilter).catch(() => ({ events: [], count: 0, total: 0, stats: {} })),
        getSecurityAlerts({ status: 'ACTIVE', limit: 50 }).catch(() => ({ alerts: [], total: 0 })),
        getSecurityConfiguration().catch(() => ({ checks: [] })),
      ]);
      setOverview(ov || { score: 50, category: 'WARNING', configuration: { checks: [] }, audit_summary: {}, alerts_summary: {}, active_sessions: [] });
      setAudit(aud);
      setAlertsData(al);
      setConfig(cfg);
    } catch (err) {
      setApiError(err.message || 'Failed to load security data');
    } finally {
      setLoading(false);
    }
  }, [auditFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleAcknowledge = async (id) => {
    try { await acknowledgeSecurityAlert(id, 'operator'); await loadData(); } catch (e) { setApiError('Failed to acknowledge alert'); }
  };

  const handleResolve = async (id) => {
    try { await resolveSecurityAlert(id, 'operator'); await loadData(); } catch (e) { setApiError('Failed to resolve alert'); }
  };

  const handleApplyRetention = async (days) => {
    try { await applySecurityRetention(days); await loadData(); } catch (e) { setApiError('Retention apply failed'); }
  };

  const handleAuditFilter = (f) => {
    setAuditFilter({ limit: 50, offset: 0, ...f });
  };

  if (loading && !overview) {
    return <div className="page-section"><div className="data-banner loading">Loading security center...</div></div>;
  }

  const score = overview?.score || { score: 50, category: 'WARNING', factors: [] };
  const alertsSummary = overview?.alerts_summary || { total: 0, active: 0, resolved: 0, by_severity: {} };
  const auditSummary = overview?.audit_summary || { total: 0, by_type: {}, by_user: {}, recent: [], failed_count: 0 };
  const sessions = overview?.active_sessions || [];
  const currentUser = getStoredUser();

  return (
    <div className="security-page">
      <div className="page-header">
        <h1>Security & Audit Center</h1>
        <p className="page-subtitle">Real-time security monitoring and audit trail</p>
        <p className="page-subtitle">Authentication: ENABLED Â· RBAC role: {currentUser?.role || 'UNKNOWN'} Â· Provider modes are reported from backend configuration.</p>
        {apiError && <div className="data-banner warning">{apiError} <button onClick={loadData}>Retry</button></div>}
      </div>

      <SecurityScore score={score.score} category={score.category} factors={score.factors} />

      <div className="stats-row">
        <div className="stat-card"><span className="stat-card-title">Active Alerts</span><span className="stat-card-value">{alertsSummary.active}</span><span className="stat-card-label">{alertsSummary.total} total</span></div>
        <div className="stat-card"><span className="stat-card-title">Audit Events</span><span className="stat-card-value">{auditSummary.total}</span><span className="stat-card-label">Failed: {auditSummary.failed_count}</span></div>
        <div className="stat-card"><span className="stat-card-title">Active Sessions</span><span className="stat-card-value">{sessions.length}</span><span className="stat-card-label">last 24h</span></div>
        <div className="stat-card"><span className="stat-card-title">Security Status</span><span className={`stat-card-status ${score.category.toLowerCase()}`}>{score.category}</span></div>
      </div>

      <div className="panels-row">
        <ConfigurationStatus checks={config.checks} />
        <SecurityAlerts alertsData={alertsData} onAcknowledge={handleAcknowledge} onResolve={handleResolve} />
      </div>

      <AuditLog audit={audit} onFilter={handleAuditFilter} />

      <div className="sub-section">
        <h3>Incident Audit Trail</h3>
        <AuditTrail trail={audit.events.filter(e => e.event_type.includes('INCIDENT'))} />
      </div>

      <div className="sub-section retention">
        <h3>Data Retention</h3>
        <p>Audit retention: 30 days (default). Apply retention policy to delete events older than N days.</p>
        <div className="retention-actions">
          <button className="secondary-btn" onClick={() => handleApplyRetention(7)}>Apply 7-day retention</button>
          <button className="secondary-btn" onClick={() => handleApplyRetention(30)}>Apply 30-day retention</button>
          <button className="secondary-btn" onClick={() => handleApplyRetention(90)}>Apply 90-day retention</button>
        </div>
      </div>
    </div>
  );
};

export default SecurityPage;
