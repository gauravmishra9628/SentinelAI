import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { useWebSocket } from '../services/websocket';
import {
  getIncidents,
  getIncidentSummary,
  getHealth,
} from '../services/api';
import './IncidentsPage.css';

const formatTs = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

const formatRel = (value) => {
  if (!value) return '—';
  try {
    const diff = (Date.now() - new Date(value).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 36400)}d ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return value;
  }
};

const severityClass = (value) => `incident-severity-${String(value || '').toLowerCase()}`;
const statusClass = (value) => `incident-status-${String(value || '').toLowerCase()}`;

const INCIDENT_STATUSES = {
  NEW: 'New',
  ACKNOWLEDGED: 'Acknowledged',
  INVESTIGATING: 'Investigating',
  RESOLVED: 'Resolved',
};

const IncidentsPage = () => {
  const navigate = useNavigate();
  const { connectionState, events } = useWebSocket(['incident', 'alert', 'risk_update']);
  const [incidents, setIncidents] = useState([]);
  const [incidentSummary, setIncidentSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState('');
  const [isBackendOnline, setIsBackendOnline] = useState(null);
  const [incidentStatusFilter, setIncidentStatusFilter] = useState('ALL');
  const [incidentSeverityFilter, setIncidentSeverityFilter] = useState('ALL');

  const loadIncidentData = useCallback(async () => {
    setLoading(true);
    setApiError('');

    try {
      const [health, incData, summaryData] = await Promise.all([
        getHealth().catch(() => ({ status: 'error' })),
        getIncidents({ limit: 50 }).catch(() => ({ incidents: [] })),
        getIncidentSummary().catch(() => ({})),
      ]);

      const incidentsList = Array.isArray(incData?.incidents) ? incData.incidents : [];
      setIncidents(incidentsList);
      setIncidentSummary(summaryData);
      setIsBackendOnline(health.status === 'ok');
    } catch (error) {
      setApiError(error.message || 'Failed to load incidents data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIncidentData();
  }, [loadIncidentData]);

  useEffect(() => {
    // Reload when relevant WebSocket events come through
    const latestIncidentEvent = events.get('incident')?.[0];
    const latestAlertEvent = events.get('alert')?.[0];
    if (latestIncidentEvent || latestAlertEvent) {
      loadIncidentData();
    }
  }, [events, loadIncidentData]);

  const selectedIncident = useMemo(() => {
    return incidents.find(
      (item) =>
        item.severity === incidentSeverityFilter ||
        incidentSeverityFilter === 'ALL'
    );
  }, [incidents, incidentSeverityFilter]);

  const incidentCounts = useMemo(() => {
    if (!incidentSummary?.counts) return {};
    const counts = incidentSummary.counts;
    return {
      total: counts?.total || 0,
      new: counts?.new || 0,
      acknowledged: counts?.acknowledged || 0,
      investigating: counts?.investigating || 0,
      resolved: counts?.resolved || 0,
      active: (counts?.new || 0) + (counts?.acknowledged || 0) + (counts?.investigating || 0),
    };
  }, [incidentSummary]);

  const statusOptions = [
    { value: 'ALL', label: 'All' },
    { value: 'NEW', label: 'New' },
    { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
    { value: 'INVESTIGATING', label: 'Investigating' },
    { value: 'RESOLVED', label: 'Resolved' },
  ];

  const severityOptions = [
    { value: 'ALL', label: 'All' },
    { value: 'CRITICAL', label: 'Critical' },
    { value: 'HIGH', label: 'High' },
    { value: 'MEDIUM', label: 'Medium' },
    { value: 'LOW', label: 'Low' },
  ];

  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      const statusMatch =
        incidentStatusFilter === 'ALL' || inc.status === incidentStatusFilter;
      const severityMatch =
        incidentSeverityFilter === 'ALL' || inc.severity === incidentSeverityFilter;
      return statusMatch && severityMatch;
    });
  }, [incidents, incidentStatusFilter, incidentSeverityFilter]);

  const criticalCount = useMemo(
    () =>
      filteredIncidents.filter(
        (i) => i.severity === 'CRITICAL' && !['RESOLVED'].includes(i.status)
      ).length,
    [filteredIncidents]
  );

  const highCount = useMemo(
    () =>
      filteredIncidents.filter(
        (i) => i.severity === 'HIGH' && !['RESOLVED'].includes(i.status)
      ).length,
    [filteredIncidents]
  );

  return (
    <>
      <Header systemStatus={isBackendOnline} />
      <section className="page-section incidents-page">
        <div className="page-header">
          <div>
            <h1 className="page-title">Incidents</h1>
            <p className="page-subtitle">
              Track and manage road-safety incidents from detection to resolution
            </p>
          </div>
          <div className="page-header-actions">
            <button
              className="secondary-btn"
              onClick={() => navigate('/investigation')}
            >
              AI Investigation
            </button>
          </div>
        </div>

        {apiError && (
          <div className="data-banner warning">
            <span>{apiError}</span>
            <button onClick={loadIncidentData}>Dismiss</button>
          </div>
        )}

        <div className="incidents-summary-grid">
          <div className="summary-card">
            <h3>Total Incidents</h3>
            <p className="summary-value">{incidentCounts.total}</p>
          </div>
          <div className="summary-card">
            <h3>Active Incidents</h3>
            <p className="summary-value">{incidentCounts.active}</p>
          </div>
          <div className="summary-card">
            <h3>Critical</h3>
            <p className="summary-value">{criticalCount}</p>
          </div>
          <div className="summary-card">
            <h3>High</h3>
            <p className="summary-value">{highCount}</p>
          </div>
        </div>

        <div className="incidents-filters">
          <select
            value={incidentStatusFilter}
            onChange={(e) => setIncidentStatusFilter(e.target.value)}
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={incidentSeverityFilter}
            onChange={(e) => setIncidentSeverityFilter(e.target.value)}
          >
            {severityOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button className="secondary-btn" onClick={loadIncidentData}>
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="data-loading">
            <div className="spinner" />
            <span>Loading incidents...</span>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="empty-state">
            <h3>No incidents found</h3>
            <p>No incidents matching the selected filters. Incidents are created when AI detects HIGH or CRITICAL road-safety risks.</p>
          </div>
        ) : (
          <div className="incidents-table">
            <div className="table-header">
              <div>ID</div>
              <div>Type</div>
              <div>Severity</div>
              <div>Status</div>
              <div>Risk</div>
              <div>Camera</div>
              <div>Location</div>
              <div>Created</div>
              <div>Actions</div>
            </div>
            <div className="table-body">
              {filteredIncidents.map((inc) => (
                <div key={inc.id} className="table-row">
                  <div className="cell cell-id">{inc.id}</div>
                  <div className="cell">{inc.incident_type || 'Road Safety'}</div>
                  <div className={`cell badge badge-${inc.severity.toLowerCase()}`}>
                    {inc.severity}
                  </div>
                  <div className={`cell badge ${statusClass(inc.status)}`}>
                    {INCIDENT_STATUSES[inc.status] || inc.status}
                  </div>
                  <div className="cell">{inc.risk_score}</div>
                  <div className="cell">{inc.camera_id || '—'}</div>
                  <div className="cell" style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {inc.location || '—'}
                  </div>
                  <div className="cell">{formatTs(inc.timestamp)}</div>
                  <div className="cell cell-actions">
                    <button
                      className="action-btn"
                      onClick={() => navigate(`/incidents/${inc.id}`)}
                    >
                      Details
                    </button>
                    {inc.status === 'NEW' && (
                      <button
                        className="action-btn action-btn--secondary"
                        onClick={() => navigate(`/investigation/${inc.id}`)}
                      >
                        Investigate
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </>
  );
};

export default IncidentsPage;