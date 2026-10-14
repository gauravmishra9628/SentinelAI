import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { useWebSocket } from '../services/websocket';
import {
  getEmergencyResponses,
  getEmergencyResponse,
  getEmergencyUnits,
  acknowledgeEmergency,
  escalateEmergency,
  updateEmergencyStatus,
  assignEmergencyUnit,
  addEmergencyNote,
  resolveEmergency,
  getStoredUser,
} from '../services/api';
import './EmergencyResponsePage.css';

const PRIORITY_ORDER = { P1: 1, P2: 2, P3: 3, P4: 4 };
const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const ACTIVE_STATUSES = new Set(['PENDING', 'ACKNOWLEDGED', 'DISPATCH_RECOMMENDED', 'DISPATCHED', 'RESPONDING', 'ON_SCENE']);

const formatTime = (value) => {
  if (!value) return '—';
  try { return new Date(value).toLocaleString(); } catch { return value; }
};

const elapsed = (createdAt, endAt) => {
  if (!createdAt) return '—';
  const seconds = Math.max(0, ((endAt ? new Date(endAt) : new Date()) - new Date(createdAt)) / 1000);
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
};

const severityClass = (value) => `er-severity er-severity-${String(value || '').toLowerCase()}`;
const statusClass = (value) => `er-status er-status-${String(value || '').toLowerCase()}`;

const SummaryCard = ({ label, value, tone }) => (
  <div className={`er-summary-card ${tone || ''}`}>
    <span>{label}</span>
    <strong>{value}</strong>
  </div>
);

const EmergencyResponsePage = () => {
  const navigate = useNavigate();
  const { connectionState, events } = useWebSocket(['emergency_response']);
  const [responses, setResponses] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [selected, setSelected] = useState(null);
  const [units, setUnits] = useState([]);
  const [analytics, setAnalytics] = useState({});
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ACTIVE');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [clock, setClock] = useState(Date.now());
  const currentUser = getStoredUser();

  const loadQueue = useCallback(async () => {
    try {
      const [queue, unitData] = await Promise.all([
        getEmergencyResponses({ status: statusFilter === 'ACTIVE' ? undefined : statusFilter, severity: severityFilter }),
        getEmergencyUnits(),
      ]);
      const nextResponses = Array.isArray(queue?.responses) ? queue.responses : [];
      setResponses(nextResponses);
      setAnalytics(queue?.analytics || {});
      setUnits(Array.isArray(unitData?.units) ? unitData.units : []);
      setSelectedId((current) => current || nextResponses[0]?.id || '');
    } catch (err) {
      setError(err.message || 'Emergency response service unavailable');
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter]);

  const loadSelected = useCallback(async () => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    try {
      setSelected(await getEmergencyResponse(selectedId));
    } catch (err) {
      setError(err.message || 'Unable to load response details');
    }
  }, [selectedId]);

  useEffect(() => { loadQueue(); }, [loadQueue]);
  useEffect(() => { loadSelected(); }, [loadSelected]);
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    const latest = events.get('emergency_response')?.[0];
    if (latest) {
      loadQueue();
      loadSelected();
    }
  }, [events, loadQueue, loadSelected]);

  const filteredResponses = useMemo(() => responses.filter((response) => {
    if (severityFilter !== 'ALL' && response.severity !== severityFilter) return false;
    if (statusFilter === 'ACTIVE' && !ACTIVE_STATUSES.has(response.status)) return false;
    if (statusFilter !== 'ACTIVE' && statusFilter !== 'ALL' && response.status !== statusFilter) return false;
    return true;
  }), [responses, severityFilter, statusFilter]);

  const availableUnits = units.filter((unit) => unit.status === 'AVAILABLE');
  const activeCount = responses.filter((item) => ACTIVE_STATUSES.has(item.status)).length;
  const respondingCount = responses.filter((item) => ['RESPONDING', 'ON_SCENE'].includes(item.status)).length;
  const criticalCount = responses.filter((item) => item.severity === 'CRITICAL' && ACTIVE_STATUSES.has(item.status)).length;

  const runAction = async (action) => {
    if (!selected?.id) return;
    if (['resolve', 'cancel'].includes(action) && !window.confirm(`Confirm ${action} this emergency response case?`)) return;
    setActionLoading(true);
    setError('');
    try {
      if (action === 'acknowledge') await acknowledgeEmergency(selected.id);
      if (action === 'escalate') await escalateEmergency(selected.id);
      if (action === 'responding') await updateEmergencyStatus(selected.id, 'RESPONDING');
      if (action === 'on_scene') await updateEmergencyStatus(selected.id, 'ON_SCENE');
      if (action === 'resolve') await resolveEmergency(selected.id);
      if (action === 'cancel') await updateEmergencyStatus(selected.id, 'CANCELLED');
      await Promise.all([loadQueue(), loadSelected()]);
    } catch (err) {
      setError(err.message || 'Emergency action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const assignSelectedUnit = async (event) => {
    if (!event.target.value || !selected?.id) return;
    setActionLoading(true);
    try {
      await assignEmergencyUnit(selected.id, event.target.value);
      await Promise.all([loadQueue(), loadSelected()]);
    } catch (err) {
      setError(err.message || 'Unit is unavailable');
    } finally {
      setActionLoading(false);
      event.target.value = '';
    }
  };

  const saveNote = async () => {
    if (!note.trim() || !selected?.id) return;
    setActionLoading(true);
    try {
      await addEmergencyNote(selected.id, note);
      setNote('');
      await loadSelected();
    } catch (err) {
      setError(err.message || 'Could not save note');
    } finally {
      setActionLoading(false);
    }
  };

  const assignedUnit = selected?.assignments?.find((assignment) => !assignment.released_at);
  const statusNext = selected?.status === 'DISPATCHED' ? 'responding' : selected?.status === 'RESPONDING' ? 'on_scene' : null;

  return (
    <>
      <Header systemStatus={connectionState === 'CONNECTED'} alertCount={activeCount} />
      <section className="page-section emergency-response-page">
        <div className="page-header">
          <div>
            <div className="page-title-row"><h1 className="page-title">Emergency Response</h1><span className="er-demo-badge">SIMULATION MODE</span></div>
            <p className="page-subtitle">Operational response layer for serious SentinelAI incidents</p>
          </div>
          <div className="er-connection" aria-live="polite"><span className={`er-connection-dot ${connectionState.toLowerCase()}`} />Realtime {connectionState}</div>
        </div>

        <div className="er-runtime-status"><span>Operator: <strong>{currentUser?.role || 'UNKNOWN'}</strong></span><span>Location: <strong>SIMULATED / UNAVAILABLE</strong></span><span>Dispatch: <strong>SIMULATION</strong></span><span>Unit source: <strong>SIMULATED</strong></span></div>

        {error && <div className="data-banner warning"><span>{error}</span><button onClick={() => { setError(''); loadQueue(); }}>Retry</button></div>}

        <div className="er-summary-grid">
          <SummaryCard label="Active emergencies" value={activeCount} />
          <SummaryCard label="Critical incidents" value={criticalCount} tone="critical" />
          <SummaryCard label="Units available" value={availableUnits.length} tone="safe" />
          <SummaryCard label="Units responding" value={respondingCount} tone="warning" />
          <SummaryCard label="Avg acknowledge" value={analytics.average_acknowledgement_seconds == null ? '—' : `${analytics.average_acknowledgement_seconds}s`} />
          <SummaryCard label="Avg resolution" value={analytics.average_resolution_seconds == null ? '—' : `${Math.round(analytics.average_resolution_seconds / 60)}m`} />
        </div>

        <div className="er-filter-bar">
          <div className="er-filter-group"><span>Severity</span>{SEVERITIES.map((item) => <button key={item} className={severityFilter === item ? 'active' : ''} onClick={() => setSeverityFilter(item)}>{item}</button>)}</div>
          <label>Status <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ACTIVE">Active</option><option value="ALL">All</option>{['PENDING', 'ACKNOWLEDGED', 'DISPATCH_RECOMMENDED', 'DISPATCHED', 'RESPONDING', 'ON_SCENE', 'RESOLVED', 'CANCELLED'].map((item) => <option key={item} value={item}>{item.replace(/_/g, ' ')}</option>)}</select></label>
        </div>

        <div className="er-workspace">
          <div className="er-queue-panel">
            <div className="er-panel-heading"><h2>Active emergency queue</h2><span>{filteredResponses.length}</span></div>
            {loading ? <div className="er-empty">Loading response cases...</div> : filteredResponses.length === 0 ? <div className="er-empty">No emergency response cases match this filter.</div> : (
              <div className="er-queue-list">
                {filteredResponses.map((response) => (
                  <button key={response.id} className={`er-queue-item ${selectedId === response.id ? 'selected' : ''}`} onClick={() => setSelectedId(response.id)}>
                    <div className="er-queue-top"><strong>{response.incident_id}</strong><span className={severityClass(response.severity)}>{response.severity}</span></div>
                    <div className="er-queue-location">{response.incident?.camera_id || 'Camera unavailable'} · {response.incident?.location || 'Location metadata unavailable'} · SIMULATED LOCATION</div>
                    <div className="er-queue-bottom"><span className="er-priority">{response.priority}</span><span>Risk {response.score}/100</span><span>{elapsed(response.created_at, response.resolved_at)}</span></div>
                    <div className="er-queue-status"><span className={statusClass(response.status)}>{response.status.replace(/_/g, ' ')}</span><small>{formatTime(response.created_at)}</small></div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="er-detail-panel">
            {!selected ? <div className="er-empty">Select a response case to inspect its operational timeline.</div> : (
              <>
                <div className="er-detail-header"><div><span className="eyebrow">Response case</span><h2>{selected.incident_id}</h2><p>{selected.incident?.incident_type || 'Serious incident'} · {selected.incident?.location || 'Location metadata unavailable'}</p></div><div className="er-detail-badges"><span className={severityClass(selected.severity)}>{selected.severity}</span><span className="er-priority">{selected.priority}</span><span className={statusClass(selected.status)}>{selected.status.replace(/_/g, ' ')}</span></div></div>
                <div className="er-fact-grid"><div><span>Score</span><strong>{selected.score}/100</strong></div><div><span>Confidence</span><strong>{selected.confidence}%</strong></div><div><span>Response timer</span><strong>{elapsed(selected.created_at, selected.resolved_at, clock)}</strong></div><div><span>Created</span><strong>{formatTime(selected.created_at)}</strong></div></div>

                <div className="er-section"><h3>Transparent severity factors</h3><div className="er-factor-list">{(selected.factors || []).map((factor) => <span key={factor.label}>{factor.label}<b>+{factor.weight}</b></span>)}</div></div>
                <div className="er-section"><h3>Response timeline</h3><div className="er-timeline">{(selected.timeline || []).map((event) => <div className="er-timeline-item" key={event.id}><span className="er-timeline-marker" /><div><strong>{event.event_type.replace(/_/g, ' ')}</strong><p>{event.description}</p><small>{formatTime(event.timestamp)} · {event.actor}</small></div></div>)}</div></div>
                <div className="er-section"><h3>AI response copilot</h3><div className="er-recommendations">{(selected.recommendations || []).map((item) => <div key={`${item.action}-${item.priority}`}><strong>{item.action}</strong><span>{item.reason}</span><b>{item.priority}</b></div>)}</div></div>
              </>
            )}
          </div>

          <aside className="er-actions-panel">
            <div className="er-panel-heading"><h2>Operator actions</h2></div>
            {!selected ? <div className="er-empty">Actions appear when a case is selected.</div> : <>
              <div className="er-action-buttons">
                {selected.status === 'PENDING' && <button onClick={() => runAction('acknowledge')} disabled={actionLoading}>Acknowledge</button>}
                {['PENDING', 'ACKNOWLEDGED'].includes(selected.status) && <button onClick={() => runAction('escalate')} disabled={actionLoading}>Recommend dispatch</button>}
                {statusNext && <button onClick={() => runAction(statusNext)} disabled={actionLoading}>Mark {statusNext.replace('_', ' ')}</button>}
                {['ON_SCENE', 'RESPONDING', 'DISPATCHED', 'DISPATCH_RECOMMENDED'].includes(selected.status) && <button className="danger" onClick={() => runAction('resolve')} disabled={actionLoading}>Resolve emergency</button>}
                {ACTIVE_STATUSES.has(selected.status) && <button className="muted" onClick={() => runAction('cancel')} disabled={actionLoading}>Cancel case</button>}
              </div>
              <label className="er-field">Assign available unit<select defaultValue="" onChange={assignSelectedUnit} disabled={actionLoading || Boolean(assignedUnit)}><option value="">{assignedUnit ? `${assignedUnit.name} assigned` : 'Select a simulated unit'}</option>{availableUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name} · {unit.unit_type}</option>)}</select></label>
              {assignedUnit && <div className="er-assigned-unit"><strong>{assignedUnit.name}</strong><span>{assignedUnit.unit_type} · ETA {assignedUnit.eta_minutes || '—'} min</span><small>SIMULATED UNIT</small></div>}
              <div className="er-actions-links"><button onClick={() => navigate(`/investigation/${selected.incident_id}`)}>Open investigation</button><button onClick={() => navigate(`/incidents/${selected.incident_id}`)}>View incident</button><button onClick={() => navigate(`/live-monitoring?camera=${selected.incident?.camera_id || ''}`)}>View camera</button></div>
              <div className="er-note-box"><label htmlFor="er-note">Operator note</label><textarea id="er-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record an operational observation..." /><button onClick={saveNote} disabled={actionLoading || !note.trim()}>Add note</button></div>
              {(selected.notes || []).map((item) => <div className="er-note" key={item.id}><p>{item.note}</p><small>{item.actor} · {formatTime(item.created_at)}</small></div>)}
            </>}
          </aside>
        </div>

        <div className="er-performance"><div><h2>Response performance</h2><p>{analytics.message || 'Live metrics use persisted response timestamps.'}</p></div><div className="er-distribution"><span>Severity {Object.entries(analytics.severity_distribution || {}).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—'}</span><span>Status {Object.entries(analytics.status_distribution || {}).map(([key, value]) => `${key}: ${value}`).join(' · ') || '—'}</span></div></div>
      </section>
    </>
  );
};

export default EmergencyResponsePage;