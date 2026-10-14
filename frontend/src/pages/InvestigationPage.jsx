import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Header from '../components/Header';
import {
  getHealth,
  getIncidents,
  getAIIncidentSummary,
  getIncidentEvidenceLinks,
  investigateIncident,
  resolveIncident,
} from '../services/api';
import './InvestigationPage.css';

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
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch {
    return value;
  }
};

const InvestigationPage = () => {
  const navigate = useNavigate();
  const { incidentId: routeIncidentId } = useParams();
  const [incidentId, setIncidentId] = useState(routeIncidentId || '');
  const [incidentList, setIncidentList] = useState([]);
  const [summary, setSummary] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [apiError, setApiError] = useState('');
  const [isBackendOnline, setIsBackendOnline] = useState(null);

  const selectedIncident = useMemo(
    () => incidentList.find((item) => item.id === incidentId) || summary?.incident || null,
    [incidentId, incidentList, summary],
  );

  const loadInvestigation = useCallback(async () => {
    setLoading(true);
    setApiError('');

    try {
      const [health, incData] = await Promise.all([
        getHealth().catch(() => ({ status: 'error' })),
        getIncidents({ limit: 50 }).catch(() => ({ incidents: [] })),
      ]);

      const incidents = Array.isArray(incData?.incidents) ? incData.incidents : [];
      setIncidentList(incidents);
      setIsBackendOnline(health.status === 'ok');

      const targetId = routeIncidentId || incidents[0]?.id || '';
      setIncidentId(targetId);

      if (!targetId) {
        setSummary(null);
        setEvidence([]);
        return;
      }

      const [incidentSummary, evidenceLinks] = await Promise.all([
        getAIIncidentSummary(targetId).catch(() => ({ found: false, incident_id: targetId })),
        getIncidentEvidenceLinks(targetId).catch(() => ({ evidence: [] })),
      ]);

      setSummary(incidentSummary || { found: false, incident_id: targetId });
      setEvidence(Array.isArray(evidenceLinks?.evidence) ? evidenceLinks.evidence : []);
    } catch (error) {
      setApiError(error.message || 'Failed to load investigation data');
    } finally {
      setLoading(false);
    }
  }, [routeIncidentId]);

  useEffect(() => {
    loadInvestigation();
  }, [loadInvestigation]);

  useEffect(() => {
    if (routeIncidentId && routeIncidentId !== incidentId) {
      setIncidentId(routeIncidentId);
    }
  }, [incidentId, routeIncidentId]);

  const handleIncidentSelect = (nextId) => {
    if (!nextId) return;
    setIncidentId(nextId);
    navigate(`/investigation/${nextId}`);
  };

  const handleAction = async (action) => {
    if (!incidentId) return;
    setSaving(true);
    setApiError('');

    try {
      if (action === 'investigate') {
        await investigateIncident(incidentId);
      } else if (action === 'resolve') {
        await resolveIncident(incidentId);
      }
      await loadInvestigation();
    } catch (error) {
      setApiError(error.message || 'Action failed');
    } finally {
      setSaving(false);
    }
  };

  const summaryText = summary?.ai_summary || 'No investigation summary generated yet.';
  const detectionEvents = summary?.detection_events || [];
  const incidentCount = summary?.event_count || 0;

  return (
    <>
      <Header systemStatus={isBackendOnline} />

      <section className="page-section investigation-page">
        <div className="page-header">
          <div>
            <div className="page-title-row">
              <h1 className="page-title">AI Incident Investigation</h1>
            </div>
            <p className="page-subtitle">
              Consolidated incident timeline, AI summary, and evidence review
            </p>
          </div>

          <div className="page-header-actions">
            <button className="secondary-btn" onClick={() => navigate('/incidents')}>
              ← Incidents
            </button>
          </div>
        </div>

        {apiError && (
          <div className="data-banner warning" style={{ marginBottom: '1rem' }}>
            <span>{apiError}</span>
          </div>
        )}

        <div className="investigation-picker">
          <label htmlFor="investigation-incident-select">Incident</label>
          <select
            id="investigation-incident-select"
            value={incidentId}
            onChange={(event) => handleIncidentSelect(event.target.value)}
          >
            {incidentList.length === 0 ? (
              <option value="">No incidents available</option>
            ) : (
              incidentList.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.id} · {item.incident_type || 'Incident'} · {item.status}
                </option>
              ))
            )}
          </select>
        </div>

        {loading ? (
          <div className="incident-loading">
            <div className="spinner" />
            <span>Loading investigation findings...</span>
          </div>
        ) : !summary || !summary.found ? (
          <div className="empty-state">
            <h3>No incident selected</h3>
            <p>Select an incident to review AI findings, evidence, and timeline.</p>
          </div>
        ) : (
          <div className="investigation-grid">
            <div className="investigation-main">
              <div className="detail-card investigation-hero">
                <div>
                  <div className="eyebrow">Case overview</div>
                  <h2>Incident #{selectedIncident?.id || summary.incident_id}</h2>
                </div>
                <div className="hero-actions">
                  <button className="secondary-btn" onClick={() => navigate(`/incidents/${selectedIncident?.id || summary.incident_id}`)}>
                    View incident
                  </button>
                  <button className="primary-btn" onClick={() => handleAction('investigate')} disabled={saving}>
                    {saving ? 'Updating…' : 'Mark Investigating'}
                  </button>
                  <button className="secondary-btn" onClick={() => handleAction('resolve')} disabled={saving}>
                    Resolve
                  </button>
                </div>
              </div>

              <div className="investigation-summary-box detail-card">
                <h3>AI investigation summary</h3>
                <p>{summaryText}</p>
                <div className="summary-meta">
                  <span>Severity: {selectedIncident?.severity || summary.incident?.severity || '—'}</span>
                  <span>Risk: {selectedIncident?.risk_score ?? summary.incident?.risk_score ?? 0}/100</span>
                  <span>Status: {selectedIncident?.status || summary.incident?.status || '—'}</span>
                </div>
              </div>

              <div className="detail-card">
                <h3>Recommended action</h3>
                <div className="recommendation-panel">
                  <strong>{summary.recommended_action || 'Review the incident details and proceed.'}</strong>
                </div>
              </div>

              <div className="detail-card">
                <h3>Timeline and evidence events</h3>
                {detectionEvents.length === 0 ? (
                  <div className="empty-state-text">No detection events were captured for this incident.</div>
                ) : (
                  <div className="event-timeline">
                    {detectionEvents.map((event, index) => (
                      <div key={`${event.id || event.timestamp || index}-${event.event_type}`} className="timeline-item">
                        <div className="timeline-dot" />
                        <div className="timeline-content">
                          <div className="timeline-header">
                            <span className="timeline-event">{String(event.event_type || 'EVENT').replace(/_/g, ' ')}</span>
                          </div>
                          {event.note && <div className="timeline-note">{event.note}</div>}
                          <div className="timeline-meta">
                            <span>{formatTs(event.timestamp)}</span>
                            {event.actor && <span>by {event.actor}</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <aside className="investigation-sidebar">
              <div className="detail-card">
                <h3>Incident facts</h3>
                <div className="detail-rows">
                  <div className="detail-row"><span className="detail-label">Camera</span><span className="detail-value">{selectedIncident?.camera_id || summary.incident?.camera_id || '—'}</span></div>
                  <div className="detail-row"><span className="detail-label">Location</span><span className="detail-value">{selectedIncident?.location || summary.incident?.location || '—'}</span></div>
                  <div className="detail-row"><span className="detail-label">Type</span><span className="detail-value">{selectedIncident?.incident_type || summary.incident?.incident_type || '—'}</span></div>
                  <div className="detail-row"><span className="detail-label">Created</span><span className="detail-value">{formatTs(selectedIncident?.created_at || summary.incident?.created_at)}</span></div>
                  <div className="detail-row"><span className="detail-label">Updated</span><span className="detail-value">{formatRel(selectedIncident?.updated_at || summary.incident?.updated_at || selectedIncident?.created_at || summary.incident?.created_at)}</span></div>
                  <div className="detail-row"><span className="detail-label">Events</span><span className="detail-value">{incidentCount}</span></div>
                  <div className="detail-row"><span className="detail-label">Evidence</span><span className="detail-value">{summary.evidence_count || evidence.length}</span></div>
                </div>
              </div>

              <div className="detail-card">
                <h3>Evidence files</h3>
                {evidence.length === 0 ? (
                  <div className="empty-state-text">No linked evidence files were found.</div>
                ) : (
                  <div className="evidence-list compact">
                    {evidence.map((item) => (
                      <div key={item.id || item.file_path || item.path} className="evidence-item">
                        <div className="evidence-meta">
                          <span className="evidence-caption">{item.label || item.file_path || item.path || 'Evidence'}</span>
                          <small>{formatTs(item.created_at || item.timestamp)}</small>
                        </div>
                        {item.url && (
                          <a href={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}${item.url}`} target="_blank" rel="noreferrer">
                            Open
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </aside>
          </div>
        )}
      </section>
    </>
  );
};

export default InvestigationPage;