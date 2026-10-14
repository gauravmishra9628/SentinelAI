import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Header from '../components/Header';
import { addIncidentNote, deleteIncidentNote, getIncident, getIncidentNotes, getStoredUser } from '../services/api';
import { useWebSocket } from '../services/websocket';
import './IncidentDetailsPage.css';

const formatTime = (value) => value ? new Date(value).toLocaleString() : '—';

const IncidentDetailsPage = () => {
  const { incidentId } = useParams();
  const { connectionState, events } = useWebSocket(['incident', 'incident.created', 'emergency_response', 'emergency.updated']);
  const [payload, setPayload] = useState(null);
  const [notes, setNotes] = useState([]);
  const [noteText, setNoteText] = useState('');
  const [loading, setLoading] = useState(true);
  const [notesLoading, setNotesLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState('');
  const [error, setError] = useState('');
  const [notesError, setNotesError] = useState('');
  const [success, setSuccess] = useState('');
  const user = getStoredUser();

  const loadIncident = useCallback(async () => {
    setLoading(true);
    try { setPayload(await getIncident(incidentId)); setError(''); }
    catch (err) { setError(err.response?.data?.detail || err.message || 'Unable to load incident'); }
    finally { setLoading(false); }
  }, [incidentId]);

  const loadNotes = useCallback(async () => {
    setNotesLoading(true);
    try { const data = await getIncidentNotes(incidentId); setNotes(Array.isArray(data.notes) ? data.notes : []); setNotesError(''); }
    catch (err) { setNotesError(err.response?.data?.detail || err.message || 'Unable to load notes'); }
    finally { setNotesLoading(false); }
  }, [incidentId]);

  useEffect(() => { loadIncident(); loadNotes(); const timer = window.setInterval(() => { loadIncident(); loadNotes(); }, 30000); return () => window.clearInterval(timer); }, [loadIncident, loadNotes]);
  useEffect(() => { if (events.get('incident')?.length || events.get('incident.created')?.length || events.get('emergency_response')?.length) loadIncident(); }, [events, loadIncident]);

  const handleSave = async (event) => {
    event.preventDefault();
    const content = noteText.trim();
    if (!content) return setNotesError('Enter a note before saving.');
    if (content.length > 2000) return setNotesError('Notes must be 2,000 characters or fewer.');
    setSaving(true); setNotesError(''); setSuccess('');
    try { const result = await addIncidentNote(incidentId, content); setNotes((current) => [result.note, ...current]); setNoteText(''); setSuccess('Note saved.'); }
    catch (err) { setNotesError(err.response?.data?.detail || err.message || 'Unable to save note'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (noteId) => {
    setDeletingId(noteId); setNotesError('');
    try { await deleteIncidentNote(incidentId, noteId); setNotes((current) => current.filter((note) => note.id !== noteId)); setSuccess('Note deleted.'); }
    catch (err) { setNotesError(err.response?.data?.detail || err.message || 'Unable to delete note'); }
    finally { setDeletingId(''); }
  };

  const incident = payload?.incident;
  const stages = (payload?.events || []).map((event) => ({ label: event.event_type?.replace(/_/g, ' ') || 'Event', timestamp: event.timestamp, message: event.message }));
  return <>
    <Header systemStatus={connectionState === 'CONNECTED'} />
    <section className="page-section incident-details-page">
      <div className="page-header"><div><h1 className="page-title">Incident details</h1><p className="page-subtitle">{incidentId} · {connectionState === 'CONNECTED' ? 'LIVE' : 'REST POLLING'}</p></div></div>
      {error && <div className="data-banner warning">{error}</div>}
      {loading && !incident ? <div className="panel-card"><p>Loading incident data…</p></div> : !incident ? null : <>
        <div className="primary-panels">
          <div className="panel-card"><h3>{incident.title || 'Road-safety incident'}</h3><div className="risk-item"><div><strong>{incident.id}</strong><small>Alert: {incident.alert_id || '—'} · {incident.camera_id || 'Camera unavailable'}</small></div><span className={`badge ${String(incident.severity || '').toLowerCase()}`}>{incident.severity}</span></div><ul className="stack-list"><li>Risk: {incident.risk_score}/100 ({incident.risk_level})</li><li>Location: {incident.location || 'Location metadata unavailable'}</li><li>Detected: {formatTime(incident.timestamp)}</li><li>Status: {incident.status}</li><li>Detections: {Array.isArray(incident.detections) ? incident.detections.map((d) => d.class).join(', ') || 'None recorded' : 'None recorded'}</li></ul></div>
          <div className="panel-card"><h3>Incident timeline</h3>{stages.length ? <ol className="stack-list">{stages.map((stage, index) => <li key={`${stage.timestamp}-${index}`}><strong>{stage.label}</strong><small>{formatTime(stage.timestamp)}{stage.message ? ` · ${stage.message}` : ''}</small></li>)}</ol> : <p>No timeline events recorded.</p>}<h3>Evidence</h3>{payload.evidence?.length ? <ul className="stack-list">{payload.evidence.map((item) => <li key={item.id}>{item.file_path} · {formatTime(item.created_at)}</li>)}</ul> : <p>No evidence recorded.</p>}</div>
        </div>
        <div className="panel-card incident-notes-card">
          <div className="notes-heading"><div><h3>Quick incident notes</h3><p className="panel-muted">Capture concise observations for the response team.</p></div><span className="notes-role">{user?.role || 'Authenticated user'}</span></div>
          {success && <div className="notes-success" role="status">{success}</div>}
          {notesError && <div className="data-banner warning" role="alert">{notesError}</div>}
          {user?.role !== 'VIEWER' && <form className="note-form" onSubmit={handleSave}><textarea value={noteText} onChange={(event) => setNoteText(event.target.value)} maxLength={2000} placeholder="Add a short operational note…" aria-label="Incident note" /><div className="note-form-footer"><span>{noteText.length}/2000</span><button className="action-btn" type="submit" disabled={saving || !noteText.trim()}>{saving ? 'Saving…' : 'Save note'}</button></div></form>}
          {notesLoading ? <p className="panel-muted">Loading notes…</p> : notes.length === 0 ? <p className="panel-muted">No notes have been added to this incident.</p> : <div className="notes-list">{notes.map((note) => { const canDelete = user?.role === 'ADMIN' || note.author_id === user?.id; return <article className="note-item" key={note.id}><div className="note-content"><p>{note.content}</p><small>{note.author_username || 'Unknown author'} · {formatTime(note.created_at)}</small></div>{canDelete && <button className="note-delete" type="button" onClick={() => handleDelete(note.id)} disabled={deletingId === note.id}>{deletingId === note.id ? 'Deleting…' : 'Delete'}</button>}</article>; })}</div>}
        </div>
      </>}
    </section>
  </>;
};

export default IncidentDetailsPage;
