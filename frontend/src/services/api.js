/**
 * SentinelAI API Service
 *
 * Axios-based API client for the SentinelAI backend.
 * Two client instances:
 *   - api        : JSON requests (default)
 *   - uploadApi  : multipart/form-data uploads (no JSON Content-Type)
 *
 * Environment variable:
 *   VITE_API_URL - Override the backend URL (default: http://127.0.0.1:8000)
 */

import axios from 'axios';

// Base URL - override with VITE_API_URL env variable
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// JSON-based client (default for most calls)
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 8000,
});

// FormData-based client for file uploads (no fixed Content-Type;
// axios will set the multipart boundary automatically).
const uploadApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // uploads may take longer
});

const getAccessToken = () => window.localStorage.getItem('sentinel_access_token');

const attachToken = (config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
};

api.interceptors.request.use(attachToken);
uploadApi.interceptors.request.use(attachToken);

// --- Response interceptor: normalize network errors ---
const networkErrorHandler = (error) => {
  if (!error.response) {
    return Promise.reject(new Error('Backend connection unavailable'));
  }
  if (error.response.status === 401 && !error.config?.url?.includes('/api/auth/login')) {
    logout();
    window.dispatchEvent(new CustomEvent('sentinel-auth-expired'));
  }
  return Promise.reject(error);
};

api.interceptors.response.use(
  (response) => response,
  networkErrorHandler,
);

uploadApi.interceptors.response.use(
  (response) => response,
  networkErrorHandler,
);

export const login = (username, password) =>
  api.post('/api/auth/login', { username, password }).then((response) => {
    const data = response.data;
    window.localStorage.setItem('sentinel_access_token', data.access_token);
    window.localStorage.setItem('sentinel_user', JSON.stringify(data.user));
    return data;
  });

export const getCurrentUser = () =>
  api.get('/api/auth/me').then((response) => {
    window.localStorage.setItem('sentinel_user', JSON.stringify(response.data));
    return response.data;
  });

export const getStoredUser = () => {
  try { return JSON.parse(window.localStorage.getItem('sentinel_user') || 'null'); } catch { return null; }
};

export const logout = () => {
  window.localStorage.removeItem('sentinel_access_token');
  window.localStorage.removeItem('sentinel_user');
};

// ============================================================
// Health & Dashboard
// ============================================================

/** Health probe - detects backend availability. */
export const getHealth = () =>
  api.get('/api/health').then((response) => response.data);

/** Aggregated dashboard - statistics, monitoring, risks, alerts, analytics. */
export const getDashboard = () =>
  api.get('/api/dashboard').then((response) => response.data);

// ============================================================
// Live Monitoring
// ============================================================

/** Live camera monitoring data. */
export const getLiveMonitoring = () =>
  api.get('/api/live-monitoring').then((response) => response.data);

// ============================================================
// Risk Detection
// ============================================================

/** AI risk detection events. */
export const getRiskDetection = () =>
  api.get('/api/risk-detection').then((response) => response.data);

// ============================================================
// Alerts
// ============================================================

/** Recent safety alerts. */
export const getAlerts = () =>
  api.get('/api/alerts').then((response) => response.data);

// ============================================================
// Analytics
// ============================================================

/** Road safety analytics - metrics and trends. */
export const getAnalytics = () =>
  api.get('/api/analytics').then((response) => response.data);

// ============================================================
// Demo Mode / Camera Preview Fallback
// ============================================================

/**
 * Get demo mode info including available demo images for the
 * camera preview fallback. Used when YOLO/Ultralytics is unavailable
 * and the user has not granted webcam access.
 *
 * @returns {Promise<{
 *   demo_mode: boolean,
 *   ai_mode: string,             // "YOLO" | "DEMO" | "OFFLINE"
 *   yolo_available: boolean,
 *   model_loaded: boolean,
 *   demo_images: Array<{ id, name, description, url, size_kb }>,
 *   default_demo_image: string | null,
 *   message: string,
 * }>}
 */
export const getDemoInfo = () =>
  api.get('/api/demo/info').then((response) => response.data);

/** Returns the default demo frame URL for the camera preview. */
export const getDemoFrame = () =>
  api.get('/api/demo/frame').then((response) => response.data);

// ============================================================
// AI Engine
// ============================================================

/** AI engine status and telemetry. */
export const getAIEngineStatus = () =>
  api.get('/api/ai-engine/status').then((response) => response.data);

/**
 * Get model capabilities report (which features the loaded model supports).
 *
 * Returns a report listing:
 *  - ai_mode ("YOLO" | "DEMO" | "OFFLINE")
 *  - model_classes_count
 *  - supported_event_types (VEHICLE_DENSITY, PEDESTRIAN_RISK, etc.)
 *  - features (helmet_detection, accident_detection, ..., collision_proximity_analysis)
 *  - limitations (human-readable description of what the model CANNOT do)
 *
 * The frontend uses this to display "Not available with current model"
 * instead of fake data.
 *
 * @returns {Promise<{
 *   ai_mode: string,
 *   model_classes_count: number,
 *   supported_event_types: string[],
 *   features: { helmet_detection: boolean, accident_detection: boolean, ... },
 *   limitations: string,
 * }>}
 */
export const getModelCapabilities = () =>
  api.get('/api/model/capabilities').then((response) => response.data);

// ============================================================
// Frame Detection (POST /api/detect)
// ============================================================

/**
 * Send a single video frame to the AI detector via multipart/form-data.
 *
 * Preferred path for browser webcam frames - avoids base64 bloat.
 *
 * @param {Blob|File} frame - JPEG/PNG image blob (e.g. canvas.toBlob())
 * @param {string} [filename='frame.jpg'] - Filename sent in the multipart payload
 * @param {string} [cameraId='camera-1'] - Camera identifier for multi-camera support
 * @returns {Promise<{
 *   success: boolean,
 *   risk_level: string,
 *   risk_score: number,
 *   detections: Array<{
 *     class: string,
 *     confidence: number,
 *     x1: number, y1: number, x2: number, y2: number,
 *     category?: string  // Added by ai.analysis: VEHICLE, PEDESTRIAN, etc.
 *   }>,
 *   alerts: Array<{ type: string, message: string, severity: string }>,
 *   ai_mode: 'YOLO' | 'DEMO',
 *   model: string,
 *   demo_mode: boolean,
 *   camera_id: string,
 *   filename?: string,
 *   content_type?: string,
 *   frame_timestamp?: string,
 *   // Phase 2 — Advanced analysis fields:
 *   event_type: string,             // VEHICLE_DENSITY, PEDESTRIAN_RISK, etc. or "NONE"
 *   event_factors: string[],        // human-readable signals
 *   enriched_detections: array,     // detections with `category` field
 *   evidence_id: string | null,     // evidence file id when risk is HIGH/CRITICAL
 *   evidence_url: string | null     // URL of the evidence image (relative)
 * }>}
 */
export const detectFrame = (frame, filename = 'frame.jpg', cameraId = 'camera-1') => {
  const formData = new FormData();
  formData.append('file', frame, filename);
  formData.append('camera_id', cameraId);
  return uploadApi
    .post('/api/detect', formData)
    .then((response) => response.data);
};

/**
 * Send a frame as a JSON payload (base64-encoded).
 *
 * Backward-compatible path used by older callers; the backend exposes
 * this as POST /api/detect/json.
 *
 * @param {string} imageBase64 - Base64-encoded JPEG image (without data URI prefix)
 * @param {string} [imageFormat='jpeg'] - Image format
 */
export const detectFrameJson = (imageBase64, imageFormat = 'jpeg') => {
  const cleanBase64 = String(imageBase64 || '').replace(
    /^data:image\/\w+;base64,/,
    '',
  );
  return api
    .post('/api/detect/json', { image: cleanBase64, image_format: imageFormat })
    .then((response) => response.data);
};

// ============================================================
// Detection Stats
// ============================================================

/** Detection statistics for monitoring. */
export const getDetectionStats = () =>
  api.get('/api/detection-stats').then((response) => response.data);

// ============================================================
// Alert Management API
// ============================================================

/**
 * Get list of alerts with optional filtering.
 * @param {Object} params - Query parameters
 * @param {number} params.limit - Maximum number of alerts to return
 * @param {number} params.offset - Number of alerts to skip
 * @param {string} params.status - Filter by status (ACTIVE, ACKNOWLEDGED, RESOLVED)
 * @param {string} params.severity - Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)
 */
export const getAlertList = (params = {}) =>
  api.get('/api/alerts', { params }).then((response) => response.data);

/**
 * Get a single alert by ID.
 * @param {string} alertId - Alert ID
 */
export const getAlertById = (alertId) =>
  api.get(`/api/alerts/${alertId}`).then((response) => response.data);

/**
 * Acknowledge an alert.
 * @param {string} alertId - Alert ID
 */
export const acknowledgeAlert = (alertId) =>
  api.post(`/api/alerts/${alertId}/acknowledge`).then((response) => response.data);

/**
 * Resolve an alert.
 * @param {string} alertId - Alert ID
 */
export const resolveAlert = (alertId) =>
  api.post(`/api/alerts/${alertId}/resolve`).then((response) => response.data);

/**
 * Delete an alert.
 * @param {string} alertId - Alert ID
 */
export const deleteAlert = (alertId) =>
  api.delete(`/api/alerts/${alertId}`).then((response) => response.data);

/**
 * Clear all alerts.
 */
export const clearAllAlerts = () =>
  api.delete('/api/alerts').then((response) => response.data);

/**
 * Get alert summary statistics.
 */
export const getAlertSummary = () =>
  api.get('/api/alerts/summary').then((response) => response.data);

// ============================================================
// Detection History API
// ============================================================

/**
 * Get detection history.
 * @param {Object} params - Query parameters
 * @param {number} params.limit - Maximum number of events to return
 * @param {number} params.offset - Number of events to skip
 * @param {string} params.risk_level - Filter by risk level
 * @param {number} params.min_risk_score - Minimum risk score
 */
export const getDetectionHistory = (params = {}) =>
  api.get('/api/detection-history', { params }).then((response) => response.data);

// ============================================================
// Incidents API
// ============================================================

/** List incidents with optional filters. */
export const getIncidents = (params = {}) =>
  api.get('/api/incidents', { params }).then((r) => r.data);

/** Get a single incident with its event history and evidence. */
export const getIncident = (incidentId) =>
  api.get(`/api/incidents/${incidentId}`).then((r) => r.data);

/** Acknowledge an incident. */
export const acknowledgeIncident = (incidentId, note) =>
  api.post(`/api/incidents/${incidentId}/acknowledge`, { note }).then((r) => r.data);

/** Mark incident as investigating. */
export const investigateIncident = (incidentId, note) =>
  api.post(`/api/incidents/${incidentId}/investigate`, { note }).then((r) => r.data);

/** Resolve an incident. */
export const resolveIncident = (incidentId, note) =>
  api.post(`/api/incidents/${incidentId}/resolve`, { note }).then((r) => r.data);

/** Assign an incident. */
export const assignIncident = (incidentId, assignedTo, note) =>
  api.post(`/api/incidents/${incidentId}/assign`, { assigned_to: assignedTo, note }).then((r) => r.data);

/** Get event history for an incident. */
export const getIncidentEvents = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/events`).then((r) => r.data);

/** Get evidence items for an incident. */
export const getIncidentEvidence = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/evidence`).then((r) => r.data);

/** List quick notes for an incident. */
export const getIncidentNotes = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/notes`).then((r) => r.data);

/** Add a quick note to an incident. */
export const addIncidentNote = (incidentId, content) =>
  api.post(`/api/incidents/${incidentId}/notes`, { content }).then((r) => r.data);

/** Delete an incident note when permitted. */
export const deleteIncidentNote = (incidentId, noteId) =>
  api.delete(`/api/incidents/${incidentId}/notes/${noteId}`).then((r) => r.data);

/** Create an incident from an existing alert. */
export const createIncidentFromAlert = (alertId) =>
  api.post(`/api/incidents/from-alert/${alertId}`).then((r) => r.data);

/** Get incident summary counts. */
export const getIncidentSummary = () =>
  api.get('/api/incidents/summary').then((r) => r.data);

/** List all evidence records across all incidents (for Evidence Center). */
export const getAllEvidence = (params = {}) =>
  api.get('/api/evidence', { params }).then((r) => r.data);

// ============================================================
// Evidence API
// ============================================================

/** Upload evidence snapshot to an incident (multipart). */
export const uploadEvidence = (incidentId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post(`/api/incidents/${incidentId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

/** Get the evidence image blob URL for display. */
export const getEvidenceUrl = (filename) => `${API_BASE_URL}/api/evidence/${encodeURIComponent(filename)}`;

/** Trigger a browser download of an evidence file (no path exposed to client). */
export const downloadEvidence = async (filename, suggestedName) => {
  const url = getEvidenceUrl(filename);
  const response = await api.get(url, { responseType: 'blob' });
  const blobUrl = window.URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = blobUrl;
  a.download = suggestedName || filename.split('/').pop() || 'evidence.jpg';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.setTimeout(() => window.URL.revokeObjectURL(blobUrl), 0);
};

// ============================================================
// Export API
// ============================================================

/** Export an incident report as JSON. */
export const exportIncidentReport = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/export`).then((r) => r.data);

// ============================================================
// Camera Health API
// ============================================================

/** Get health status for all cameras. */
export const getCameraHealth = () =>
  api.get('/api/cameras/health').then((r) => r.data);

/** Record a heartbeat from a camera. */
export const cameraHeartbeat = (cameraId) =>
  api.post(`/api/cameras/${cameraId}/heartbeat`).then((r) => r.data);

// ============================================================
// System Status API
// ============================================================

/** Get complete system status for the AI System Status panel. */
export const getSystemStatus = () =>
  api.get('/api/system/status').then((r) => r.data);

// ============================================================
// Comprehensive Analytics API
// ============================================================

/** Get comprehensive analytics (detections, alerts, incidents, risk trend). */
export const getComprehensiveAnalytics = () =>
  api.get('/api/analytics/comprehensive').then((r) => r.data);

// ============================================================
// Risk Timeline API
// ============================================================

/** Get risk timeline events for the dashboard timeline panel. */
export const getRiskTimeline = (limit = 50) =>
  api.get('/api/risk-timeline', { params: { limit } }).then((r) => r.data);

// ============================================================
// Cameras API
// ============================================================

/** List known cameras with their current status. */
export const getCameras = () =>
  api.get('/api/cameras').then((response) => response.data);

/**
 * Update a camera's status.
 * @param {string} cameraId
 * @param {string} status - ONLINE | OFFLINE | ERROR | STARTING | STOPPED
 */
export const updateCameraStatus = (cameraId, status) =>
  api.post(`/api/cameras/${cameraId}/status`, null, { params: { status } })
    .then((response) => response.data);

/**
 * Build a fully-qualified stream URL for a camera.
 * The path is /api/cameras/{cameraId}/stream - a multipart/x-mixed-replace
 * MJPEG stream served by the backend.
 * @param {string} cameraId
 * @returns {string|null} absolute URL, or null if cameraId is falsy
 */
export const getCameraStreamUrl = (cameraId) => {
  if (!cameraId) return null;
  return `${API_BASE_URL}/api/cameras/${encodeURIComponent(cameraId)}/stream`;
};

// ============================================================
// Analytics API
// ============================================================

/**
 * Get dashboard analytics (metrics and trends).
 */
export const getDashboardAnalytics = () =>
  api.get('/api/analytics/dashboard').then((response) => response.data);

/**
 * Get full analytics data including alert counts and detection stats.
 */
export const getFullAnalytics = () =>
  api.get('/api/analytics/full').then((response) => response.data);

/**
 * Get risk trend data.
 * @param {number} limit - Number of hours to look back (default 24)
 */
export const getRiskTrend = (limit = 24) =>
  api.get('/api/analytics/risk-trend', { params: { limit } }).then((response) => response.data);

// ============================================================
// AI Traffic Analytics Endpoints
// ============================================================

/**
 * Get KPI overview for the analytics dashboard.
 * @param {Object} params
 * @param {string} params.period - "24h" | "7d" | "30d"
 * @param {string} params.camera_id - Filter by camera
 * @param {string} params.event_type - Filter by event type
 * @param {string} params.severity - Filter by severity
 * @param {string} params.start_date - ISO start date
 * @param {string} params.end_date - ISO end date
 */
export const getAnalyticsOverview = (params = {}) =>
  api.get('/api/analytics/overview', { params }).then((r) => r.data);

/**
 * Get time-bucketed detection counts for trend charts.
 */
export const getTrafficTrend = (params = {}) =>
  api.get('/api/analytics/traffic-trend', { params }).then((r) => r.data);

/**
 * Get per-camera risk heatmap data.
 */
export const getRiskHeatmap = (params = {}) =>
  api.get('/api/analytics/risk-heatmap', { params }).then((r) => r.data);

/**
 * Rank cameras by risk.
 */
export const getCameraRanking = (params = {}) =>
  api.get('/api/analytics/camera-ranking', { params }).then((r) => r.data);

/**
 * Get event type distribution.
 */
export const getEventDistribution = (params = {}) =>
  api.get('/api/analytics/event-distribution', { params }).then((r) => r.data);

/**
 * Find peak risk and traffic hours.
 */
export const getPeakPeriods = (params = {}) =>
  api.get('/api/analytics/peak-periods', { params }).then((r) => r.data);

/**
 * Generate a traffic safety report.
 * @param {Object} params
 * @param {string} params.report_type - "daily" | "weekly" | "monthly"
 * @param {string} params.camera_id
 * @param {string} params.start_date
 * @param {string} params.end_date
 */
export const getAnalyticsReport = (params = {}) =>
  api.get('/api/analytics/report', { params }).then((r) => r.data);

/**
 * Export analytics data as CSV or JSON blob.
 * @param {Object} params
 * @param {string} params.format - "json" | "csv"
 * @param {string} params.period
 * @param {string} params.camera_id
 * @param {string} params.start_date
 * @param {string} params.end_date
 */
export const exportAnalytics = (params = { format: 'json' }) => {
  if (params.format === 'csv') {
    return api.get('/api/analytics/export', { params, responseType: 'blob' }).then((r) => r.data);
  }
  return api.get('/api/analytics/export', { params }).then((r) => r.data);
};

// ============================================================
// Predictive Risk Engine API
// ============================================================

/**
 * Get predictive risk overview with all cameras and aggregate prediction.
 * @param {Object} params
 * @param {string} params.camera_id - Filter to one camera (optional)
 */
export const getPredictiveOverview = (params = {}) =>
  api.get('/api/predictive-risk/overview', { params }).then((r) => r.data);

/**
 * Get per-camera risk predictions with contributing factors.
 */
export const getCameraPredictions = () =>
  api.get('/api/predictive-risk/cameras').then((r) => r.data);

/**
 * Get historical prediction records.
 * @param {Object} params
 * @param {string} params.camera_id
 * @param {number} params.limit
 * @param {number} params.offset
 */
export const getPredictionHistory = (params = {}) =>
  api.get('/api/predictive-risk/history', { params }).then((r) => r.data);

/**
 * Get prediction for a specific camera.
 * @param {string} cameraId
 */
export const getCameraPrediction = (cameraId) =>
  api.get(`/api/predictive-risk/${encodeURIComponent(cameraId)}`).then((r) => r.data);

/**
 * Get prediction accuracy metrics.
 * @param {Object} params
 * @param {number} params.window_minutes - Forecast window (default 60)
 * @param {number} params.min_predictions - Min predictions needed (default 10)
 */
export const getPredictionAccuracy = (params = {}) =>
  api.get('/api/predictive-risk/accuracy', { params }).then((r) => r.data);

// ============================================================
// AI Copilot / Autonomous Safety Intelligence
// ============================================================

/**
 * Get the full structured AI Copilot context snapshot.
 */
export const getAIContext = () =>
  api.get('/api/ai/context').then((r) => r.data);

/**
 * Ask the AI Copilot a natural-language question.
 * @param {Object} body
 * @param {string} body.question - The operator's question
 * @param {Object} body.context_snapshot - Optional pre-fetched context
 */
export const askAI = (body) =>
  api.post('/api/ai/query', body).then((r) => r.data);

/**
 * Get a structured risk explanation.
 * @param {Object} params
 * @param {string} params.risk_level
 * @param {number} params.risk_score
 * @param {string} params.event_type
 */
export const getRiskExplanation = (params = {}) =>
  api.get('/api/ai/explain-risk', { params }).then((r) => r.data);

/**
 * Get operator recommendations (informational, never auto-executes).
 */
export const getAIRecommendations = () =>
  api.get('/api/ai/recommendations').then((r) => r.data);

/**
 * Get unified priority scores (0-100) for cameras.
 * @param {Object} params
 * @param {string} params.camera_id - Filter to one camera
 */
export const getPriorityScores = (params = {}) =>
  api.get('/api/ai/priority-scores', { params }).then((r) => r.data);

/**
 * Get predictive safety warnings (cameras with increasing predicted risk).
 */
export const getPredictiveWarnings = () =>
  api.get('/api/ai/predictive-warnings').then((r) => r.data);

/**
 * Get a unified safety timeline.
 * @param {Object} params
 * @param {string} params.camera_id
 * @param {string} params.severity
 * @param {string} params.event_type
 * @param {number} params.since_hours
 * @param {number} params.limit
 */
export const getSafetyTimeline = (params = {}) =>
  api.get('/api/ai/safety-timeline', { params }).then((r) => r.data);

// ============================================================
// Reports
// ============================================================

/**
 * Generate a structured daily safety report.
 */
export const getDailyReport = () =>
  api.get('/api/reports/daily').then((r) => r.data);

// ============================================================
// Incident AI Summaries
// ============================================================

/**
 * Get an AI-generated structured summary of an incident (read-only).
 * @param {string} incidentId
 */
export const getAIIncidentSummary = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/summary`).then((r) => r.data);

/**
 * Get evidence links for an incident.
 * @param {string} incidentId
 */
export const getIncidentEvidenceLinks = (incidentId) =>
  api.get(`/api/incidents/${incidentId}/evidence-links`).then((r) => r.data);

// ============================================================
// Security & Audit Center API
// ============================================================

/**
 * Get the full security dashboard: score, configuration, audit summary, alerts.
 * @returns {Promise<{
 *   score: { score: number, category: string, factors: array, ... },
 *   configuration: { checks: array, generated_at: string },
 *   audit_summary: { total: number, by_type: object, by_user: object, recent: array, failed_count: number },
 *   alerts_summary: { total: number, active: number, resolved: number, by_severity: object, recent: array },
 *   active_sessions: array,
 *   generated_at: string
 * }>}
 */
export const getSecurityOverview = () =>
  api.get('/api/security/overview').then((r) => r.data);

/**
 * Get paginated audit log entries with optional filtering.
 * @param {Object} params
 * @param {number} params.limit - Max events per page (default 50)
 * @param {number} params.offset - Pagination offset
 * @param {string} params.event_type - Filter by event type
 * @param {string} params.user_id - Filter by user
 * @param {string} params.resource_id - Filter by resource id
 * @param {string} params.severity - Filter by severity
 * @param {string} params.status - Filter by status
 * @param {string} params.since - ISO start date
 * @param {string} params.until - ISO end date
 * @param {string} params.search - Search across action/metadata/resource
 * @returns {Promise<{ events: array, count: number, total: number, limit: number, offset: number, stats: object }>}
 */
export const getSecurityAudit = (params = {}) =>
  api.get('/api/security/audit', { params }).then((r) => r.data);

/**
 * Get security alerts (suspicious activity detections).
 * @param {Object} params
 * @param {number} params.limit
 * @param {number} params.offset
 * @param {string} params.status - ACTIVE | ACKNOWLEDGED | RESOLVED
 * @param {string} params.severity - LOW | MEDIUM | HIGH | CRITICAL
 */
export const getSecurityAlerts = (params = {}) =>
  api.get('/api/security/alerts', { params }).then((r) => r.data);

/**
 * Acknowledge a security alert.
 * @param {string} alertId
 * @param {string} actor - Operator name
 */
export const acknowledgeSecurityAlert = (alertId, actor = 'operator') =>
  api.post(`/api/security/alerts/${alertId}/acknowledge`, { actor }).then((r) => r.data);

/**
 * Resolve a security alert.
 * @param {string} alertId
 * @param {string} actor - Operator name
 */
export const resolveSecurityAlert = (alertId, actor = 'operator') =>
  api.post(`/api/security/alerts/${alertId}/resolve`, { actor }).then((r) => r.data);

/**
 * Get security health score and configuration status.
 */
export const getSecurityHealth = () =>
  api.get('/api/security/health').then((r) => r.data);

/**
 * Get security configuration status (never returns secret values).
 */
export const getSecurityConfiguration = () =>
  api.get('/api/security/configuration').then((r) => r.data);

/**
 * Apply audit retention policy (destructive - deletes old audit events).
 * @param {number} retentionDays - Default 30
 */
export const applySecurityRetention = (retentionDays = 30) =>
  api.post('/api/security/retention/apply', null, { params: { retention_days: retentionDays } }).then((r) => r.data);

// ============================================================
// Emergency Response Operations
// ============================================================

export const getEmergencyResponses = (params = {}) =>
  api.get('/api/emergency-responses', { params }).then((r) => r.data);

export const createEmergencyResponse = (incidentId, actor = 'operator') =>
  api.post('/api/emergency-responses', { incident_id: incidentId, actor }).then((r) => r.data);

export const getEmergencyResponse = (responseId) =>
  api.get(`/api/emergency-responses/${responseId}`).then((r) => r.data);

export const updateEmergencyStatus = (responseId, status, actor = 'operator', note) =>
  api.patch(`/api/emergency-responses/${responseId}/status`, { status, actor, note }).then((r) => r.data);

export const acknowledgeEmergency = (responseId, actor = 'operator') =>
  api.post(`/api/emergency-responses/${responseId}/acknowledge`, { status: 'ACKNOWLEDGED', actor }).then((r) => r.data);

export const escalateEmergency = (responseId, actor = 'operator') =>
  api.post(`/api/emergency-responses/${responseId}/escalate`, { status: 'DISPATCH_RECOMMENDED', actor }).then((r) => r.data);

export const assignEmergencyUnit = (responseId, unitId, actor = 'operator') =>
  api.post(`/api/emergency-responses/${responseId}/assign-unit`, { unit_id: unitId, actor }).then((r) => r.data);

export const addEmergencyNote = (responseId, note, actor = 'operator') =>
  api.post(`/api/emergency-responses/${responseId}/note`, { note, actor }).then((r) => r.data);

export const resolveEmergency = (responseId, actor = 'operator', note) =>
  api.post(`/api/emergency-responses/${responseId}/resolve`, { status: 'RESOLVED', actor, note }).then((r) => r.data);

export const getEmergencyUnits = (params = {}) =>
  api.get('/api/emergency-units', { params }).then((r) => r.data);

export const getEmergencyAnalytics = () =>
  api.get('/api/emergency-response/analytics').then((r) => r.data);

// ============================================================
// Default export
// ============================================================
export default api;
