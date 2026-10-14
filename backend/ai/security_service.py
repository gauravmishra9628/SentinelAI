"""
SentinelAI Security & Audit Center.

Provides:
  - Persistent audit log for operator/system actions
  - Security alert detection (suspicious activity)
  - Security health score
  - System configuration status
  - Retention helpers (30-day default, not auto-applied)

Stores:
  - audit_events: timestamp, user, event_type, resource, action, status, metadata
  - security_alerts: timestamp, severity, source, reason, status

Never stores:
  - passwords, tokens, API keys, secret env values, raw video, raw evidence
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from ai.storage import get_connection


# ============================================================
# Event-type enum
# ============================================================

AUDIT_LOGIN = "LOGIN"
AUDIT_LOGOUT = "LOGOUT"
AUDIT_LOGIN_FAILED = "LOGIN_FAILED"
AUDIT_API_REQUEST = "API_REQUEST"
AUDIT_API_REQUEST_FAILED = "API_REQUEST_FAILED"
AUDIT_CAMERA_VIEW = "CAMERA_VIEW"
AUDIT_CAMERA_FULLSCREEN = "CAMERA_FULLSCREEN"
AUDIT_CAMERA_DISCONNECT = "CAMERA_DISCONNECT"
AUDIT_CAMERA_RECONNECT = "CAMERA_RECONNECT"
AUDIT_INCIDENT_VIEW = "INCIDENT_VIEW"
AUDIT_INCIDENT_ACK = "INCIDENT_ACKNOWLEDGED"
AUDIT_INCIDENT_INVESTIGATE = "INCIDENT_INVESTIGATING"
AUDIT_INCIDENT_RESOLVE = "INCIDENT_RESOLVED"
AUDIT_EVIDENCE_VIEW = "EVIDENCE_VIEW"
AUDIT_REPORT_GENERATED = "REPORT_GENERATED"
AUDIT_AI_QUERY = "AI_QUERY"
AUDIT_SETTINGS_CHANGED = "SETTINGS_CHANGED"
AUDIT_SECURITY_ALERT = "SECURITY_ALERT"
AUDIT_SECURITY_ALERT_ACK = "SECURITY_ALERT_ACK"
AUDIT_SECURITY_ALERT_RESOLVE = "SECURITY_ALERT_RESOLVED"
AUDIT_EMERGENCY_CREATED = "EMERGENCY_CREATED"
AUDIT_EMERGENCY_ACKNOWLEDGED = "EMERGENCY_ACKNOWLEDGED"
AUDIT_EMERGENCY_ESCALATED = "EMERGENCY_ESCALATED"
AUDIT_UNIT_ASSIGNED = "UNIT_ASSIGNED"
AUDIT_UNIT_REASSIGNED = "UNIT_REASSIGNED"
AUDIT_EMERGENCY_STATUS_CHANGED = "EMERGENCY_STATUS_CHANGED"
AUDIT_EMERGENCY_NOTE_ADDED = "EMERGENCY_NOTE_ADDED"
AUDIT_EVIDENCE_PRESERVED = "EVIDENCE_PRESERVED"
AUDIT_INVESTIGATION_OPENED = "INVESTIGATION_OPENED"
AUDIT_EMERGENCY_RESOLVED = "EMERGENCY_RESOLVED"
AUDIT_EMERGENCY_CANCELLED = "EMERGENCY_CANCELLED"
AUDIT_LOGIN_SUCCESS = "LOGIN_SUCCESS"
AUDIT_UNAUTHORIZED_REQUEST = "UNAUTHORIZED_REQUEST"
AUDIT_FORBIDDEN_REQUEST = "FORBIDDEN_REQUEST"
AUDIT_ROLE_CHANGED = "ROLE_CHANGED"
AUDIT_DISPATCH_REQUESTED = "DISPATCH_REQUESTED"
AUDIT_DISPATCH_SIMULATED = "DISPATCH_SIMULATED"
AUDIT_LOCATION_UPDATED = "LOCATION_UPDATED"

ALL_AUDIT_EVENT_TYPES = {
    AUDIT_LOGIN,
    AUDIT_LOGOUT,
    AUDIT_LOGIN_FAILED,
    AUDIT_API_REQUEST,
    AUDIT_API_REQUEST_FAILED,
    AUDIT_CAMERA_VIEW,
    AUDIT_CAMERA_FULLSCREEN,
    AUDIT_CAMERA_DISCONNECT,
    AUDIT_CAMERA_RECONNECT,
    AUDIT_INCIDENT_VIEW,
    AUDIT_INCIDENT_ACK,
    AUDIT_INCIDENT_INVESTIGATE,
    AUDIT_INCIDENT_RESOLVE,
    AUDIT_EVIDENCE_VIEW,
    AUDIT_REPORT_GENERATED,
    AUDIT_AI_QUERY,
    AUDIT_SETTINGS_CHANGED,
    AUDIT_SECURITY_ALERT,
    AUDIT_SECURITY_ALERT_ACK,
    AUDIT_SECURITY_ALERT_RESOLVE,
    AUDIT_EMERGENCY_CREATED,
    AUDIT_EMERGENCY_ACKNOWLEDGED,
    AUDIT_EMERGENCY_ESCALATED,
    AUDIT_UNIT_ASSIGNED,
    AUDIT_UNIT_REASSIGNED,
    AUDIT_EMERGENCY_STATUS_CHANGED,
    AUDIT_EMERGENCY_NOTE_ADDED,
    AUDIT_EVIDENCE_PRESERVED,
    AUDIT_INVESTIGATION_OPENED,
    AUDIT_EMERGENCY_RESOLVED,
    AUDIT_EMERGENCY_CANCELLED,
    AUDIT_LOGIN_SUCCESS,
    AUDIT_UNAUTHORIZED_REQUEST,
    AUDIT_FORBIDDEN_REQUEST,
    AUDIT_ROLE_CHANGED,
    AUDIT_DISPATCH_REQUESTED,
    AUDIT_DISPATCH_SIMULATED,
    AUDIT_LOCATION_UPDATED,
}

# Roles
ROLE_ADMIN = "ADMIN"
ROLE_OPERATOR = "OPERATOR"
ROLE_VIEWER = "VIEWER"
ALL_ROLES = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER}

# Default retention (days) — applied only if explicitly enabled
DEFAULT_RETENTION_DAYS = 30

# In-memory lock for the security alert rate tracking
_security_lock = threading.Lock()

# Failed request tracking for security alert detection
_failed_request_counts: dict[str, list[float]] = defaultdict(list)
_failed_login_counts: dict[str, list[float]] = defaultdict(list)

# Recent security events (short window) for deduplication
_recent_alert_keys: dict[str, float] = {}

ALERT_DEDUP_WINDOW_SECONDS = 60
FAILED_REQUEST_THRESHOLD = 20
FAILED_LOGIN_THRESHOLD = 5
RATE_WINDOW_SECONDS = 300


# ============================================================
# Database schema
# ============================================================

def _init_security_db() -> None:
    """Create audit_events + security_alerts tables if not present."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'anonymous',
                user_role TEXT NOT NULL DEFAULT 'VIEWER',
                event_type TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                status TEXT NOT NULL DEFAULT 'SUCCESS',
                severity TEXT NOT NULL DEFAULT 'INFO',
                source_ip TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_events(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource_id ON audit_events(resource_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                details TEXT,
                acknowledged_at TEXT,
                acknowledged_by TEXT,
                resolved_at TEXT,
                resolved_by TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON security_alerts(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON security_alerts(status)")

        conn.commit()


try:
    _init_security_db()
except Exception as e:
    print(f"[SentinelAI] WARNING: Security DB initialization failed: {e}")


# ============================================================
# Audit log helpers
# ============================================================

_SENSITIVE_KEYS = {
    "password", "token", "secret", "api_key", "api-key", "apikey",
    "authorization", "auth", "jwt", "bearer", "cookie", "session",
    "x-api-key", "x-auth-token", "credential", "credentials",
    "private_key", "private-key",
}


def _sanitize_metadata(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip sensitive keys and truncate long string values."""
    if meta is None:
        return None
    if not isinstance(meta, dict):
        return {"value": str(meta)[:200]}
    out: dict[str, Any] = {}
    for k, v in meta.items():
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            out[k] = "[REDACTED]"
        elif isinstance(v, str):
            out[k] = v[:300]
        else:
            out[k] = v
    return out


def _sanitize_query(query: str) -> str:
    """Sanitize AI query before storage (truncate, strip credentials)."""
    if not query:
        return ""
    text = re.sub(r"\s+", " ", query).strip()
    if len(text) > 240:
        text = text[:240] + "…"
    return text


def _next_id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def log_audit(
    event_type: str,
    user_id: str = "anonymous",
    user_role: str = ROLE_VIEWER,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    status: str = "SUCCESS",
    severity: str = "INFO",
    source_ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    """Record an audit event. Returns the event id."""
    if event_type not in ALL_AUDIT_EVENT_TYPES:
        event_type = "OTHER"
    try:
        eid = _next_id("aud")
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(_sanitize_metadata(metadata) or {})
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events
                  (id, timestamp, user_id, user_role, event_type, resource_type, resource_id,
                   action, status, severity, source_ip, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (eid, now, user_id, user_role, event_type, resource_type, resource_id,
                 action, status, severity, source_ip, meta_json),
            )
            conn.commit()
        return eid
    except Exception as e:
        print(f"[SentinelAI] ⚠️ Audit log error: {e}")
        return None


# ============================================================
# Audit query
# ============================================================

def query_audit(
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    user_id: str | None = None,
    resource_id: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Filter the audit log. Always paginated (default 50)."""
    limit = max(1, min(500, int(limit or 50)))
    offset = max(0, int(offset or 0))

    where: list[str] = []
    params: list[Any] = []

    if event_type:
        where.append("event_type = ?")
        params.append(event_type)
    if user_id:
        where.append("user_id = ?")
        params.append(user_id)
    if resource_id:
        where.append("resource_id = ?")
        params.append(resource_id)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if status:
        where.append("status = ?")
        params.append(status)
    if since:
        where.append("timestamp >= ?")
        params.append(since)
    if until:
        where.append("timestamp <= ?")
        params.append(until)
    if search:
        like = f"%{search[:80]}%"
        where.append("(action LIKE ? OR metadata LIKE ? OR resource_id LIKE ? OR user_id LIKE ?)")
        params.extend([like, like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) AS n FROM audit_events {where_sql}", params
            )
            total = cursor.fetchone()["n"]

            cursor.execute(
                f"""SELECT id, timestamp, user_id, user_role, event_type,
                           resource_type, resource_id, action, status, severity,
                           source_ip, metadata
                    FROM audit_events {where_sql}
                    ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (*params, limit, offset),
            )
            events = []
            for r in cursor.fetchall():
                events.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "user_id": r["user_id"],
                    "user_role": r["user_role"],
                    "event_type": r["event_type"],
                    "resource_type": r["resource_type"],
                    "resource_id": r["resource_id"],
                    "action": r["action"],
                    "status": r["status"],
                    "severity": r["severity"],
                    "source_ip": r["source_ip"],
                    "metadata": _safe_json_loads(r["metadata"]),
                })

            # Counts by event type
            cursor.execute(
                "SELECT event_type, COUNT(*) AS n FROM audit_events GROUP BY event_type"
            )
            by_type = {row["event_type"]: row["n"] for row in cursor.fetchall()}

            # Counts by user
            cursor.execute(
                "SELECT user_id, COUNT(*) AS n FROM audit_events GROUP BY user_id"
            )
            by_user = {row["user_id"]: row["n"] for row in cursor.fetchall()}

        return {
            "events": events,
            "count": len(events),
            "total": total,
            "limit": limit,
            "offset": offset,
            "stats": {
                "by_type": by_type,
                "by_user": by_user,
            },
        }
    except Exception as e:
        print(f"[SentinelAI] ⚠️ Audit query error: {e}")
        return {"events": [], "count": 0, "total": 0, "error": str(e)}


# ============================================================
# Security alert detection
# ============================================================

def track_failed_request(source_ip: str | None) -> None:
    """Track a failed request for threshold-based alerting."""
    if not source_ip:
        return
    now = time.time()
    with _security_lock:
        bucket = _failed_request_counts[source_ip]
        bucket.append(now)
        # Trim to window
        bucket[:] = [t for t in bucket if now - t <= RATE_WINDOW_SECONDS]
        if len(bucket) >= FAILED_REQUEST_THRESHOLD:
            _maybe_create_alert_locked(
                severity="HIGH",
                source=source_ip,
                reason=(
                    f"{len(bucket)} failed API requests in the last "
                    f"{RATE_WINDOW_SECONDS // 60} minutes from {source_ip}."
                ),
                details={"count": len(bucket), "window_seconds": RATE_WINDOW_SECONDS},
                dedup_key=f"failed_requests:{source_ip}",
            )


def track_failed_login(source_ip: str | None, username: str | None = None) -> None:
    """Track a failed login attempt."""
    if not source_ip:
        return
    now = time.time()
    with _security_lock:
        bucket = _failed_login_counts[source_ip]
        bucket.append(now)
        bucket[:] = [t for t in bucket if now - t <= RATE_WINDOW_SECONDS]
        if len(bucket) >= FAILED_LOGIN_THRESHOLD:
            _maybe_create_alert_locked(
                severity="CRITICAL",
                source=source_ip,
                reason=(
                    f"{len(bucket)} failed authentication attempts in the last "
                    f"{RATE_WINDOW_SECONDS // 60} minutes from {source_ip}."
                ),
                details={
                    "count": len(bucket),
                    "window_seconds": RATE_WINDOW_SECONDS,
                    "username_hint": (username[:8] + "…") if username else None,
                },
                dedup_key=f"failed_login:{source_ip}",
            )


def _maybe_create_alert_locked(severity: str, source: str, reason: str,
                                 details: dict | None, dedup_key: str) -> None:
    """Create a security alert if not recently duplicated. Caller holds the lock."""
    now = time.time()
    last = _recent_alert_keys.get(dedup_key, 0)
    if now - last < ALERT_DEDUP_WINDOW_SECONDS:
        return
    _recent_alert_keys[dedup_key] = now
    try:
        aid = _next_id("sa")
        ts = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO security_alerts
                     (id, timestamp, severity, source, reason, status, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (aid, ts, severity, source, reason, "ACTIVE",
                 json.dumps(details or {})),
            )
            conn.commit()
        # Also log an audit event for the alert itself
        log_audit(
            event_type=AUDIT_SECURITY_ALERT,
            user_id="system",
            user_role=ROLE_ADMIN,
            action=f"Auto-detected: {reason[:80]}",
            resource_type="security_alert",
            resource_id=aid,
            status="AUTO",
            severity=severity,
            metadata={"source": source, **(details or {})},
        )
    except Exception as e:
        print(f"[SentinelAI] ⚠️ Security alert create error: {e}")


# ============================================================
# Security alert query / manage
# ============================================================

def list_security_alerts(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    limit = max(1, min(500, int(limit or 50)))
    offset = max(0, int(offset or 0))

    where: list[str] = []
    params: list[Any] = []
    if status:
        where.append("status = ?")
        params.append(status)
    if severity:
        where.append("severity = ?")
        params.append(severity)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) AS n FROM security_alerts {where_sql}", params)
            total = cursor.fetchone()["n"]
            cursor.execute(
                f"""SELECT id, timestamp, severity, source, reason, status, details,
                           acknowledged_at, acknowledged_by, resolved_at, resolved_by
                    FROM security_alerts {where_sql}
                    ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                (*params, limit, offset),
            )
            alerts = []
            for r in cursor.fetchall():
                alerts.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "severity": r["severity"],
                    "source": r["source"],
                    "reason": r["reason"],
                    "status": r["status"],
                    "details": _safe_json_loads(r["details"]),
                    "acknowledged_at": r["acknowledged_at"],
                    "acknowledged_by": r["acknowledged_by"],
                    "resolved_at": r["resolved_at"],
                    "resolved_by": r["resolved_by"],
                })
        return {"alerts": alerts, "count": len(alerts), "total": total}
    except Exception as e:
        return {"alerts": [], "count": 0, "total": 0, "error": str(e)}


def acknowledge_security_alert(alert_id: str, actor: str) -> dict[str, Any] | None:
    try:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE security_alerts
                   SET status = 'ACKNOWLEDGED', acknowledged_at = ?, acknowledged_by = ?
                   WHERE id = ? AND status = 'ACTIVE'""",
                (now, actor, alert_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        log_audit(
            event_type=AUDIT_SECURITY_ALERT_ACK,
            user_id=actor,
            user_role=ROLE_ADMIN,
            resource_type="security_alert",
            resource_id=alert_id,
            action="acknowledge",
        )
        return {"id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_at": now, "acknowledged_by": actor}
    except Exception:
        return None


def resolve_security_alert(alert_id: str, actor: str) -> dict[str, Any] | None:
    try:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE security_alerts
                   SET status = 'RESOLVED', resolved_at = ?, resolved_by = ?
                   WHERE id = ? AND status != 'RESOLVED'""",
                (now, actor, alert_id),
            )
            conn.commit()
            if cursor.rowcount == 0:
                return None
        log_audit(
            event_type=AUDIT_SECURITY_ALERT_RESOLVE,
            user_id=actor,
            user_role=ROLE_ADMIN,
            resource_type="security_alert",
            resource_id=alert_id,
            action="resolve",
        )
        return {"id": alert_id, "status": "RESOLVED", "resolved_at": now, "resolved_by": actor}
    except Exception:
        return None


# ============================================================
# Configuration status (no secret values exposed)
# ============================================================

def get_configuration_status() -> dict[str, Any]:
    """Return SECURITY/WARNING/CRITICAL for each configuration dimension.

    NEVER returns secret values, only booleans/levels."""
    import os

    checks: list[dict[str, Any]] = []

    # 1. Authentication foundation
    auth_enabled = bool(os.getenv("AUTH_ENABLED", "true").lower() in ("1", "true", "yes"))
    auth_secret_configured = len(os.getenv("SENTINEL_AUTH_SECRET", "")) >= 32
    checks.append({
        "key": "authentication_enabled",
        "label": "Authentication enabled",
        "status": "SECURE" if auth_enabled else "WARNING",
        "description": "Bearer authentication and role enforcement are enabled." if auth_enabled else "Authentication is disabled by environment configuration.",
    })

    checks.append({
        "key": "token_secret_configured",
        "label": "JWT/token secret configured",
        "status": "SECURE" if auth_secret_configured else "CRITICAL",
        "description": "Signing secret is configured without exposing its value." if auth_secret_configured else "Set SENTINEL_AUTH_SECRET to a random value of at least 32 characters.",
    })

    checks.append({
        "key": "password_hashing",
        "label": "Password hashing",
        "status": "SECURE",
        "description": "Passwords use PBKDF2-HMAC-SHA256 with per-user salts.",
    })

    checks.append({
        "key": "rbac_middleware",
        "label": "RBAC middleware",
        "status": "SECURE" if auth_enabled and auth_secret_configured else "WARNING",
        "description": "Backend role checks are enforced before protected API handlers." if auth_enabled and auth_secret_configured else "RBAC cannot be trusted until authentication is configured.",
    })

    # 2. Legacy API secret/configuration signal
    api_key_set = bool(os.getenv("API_KEY") or os.getenv("SENTINEL_API_KEY"))
    checks.append({
        "key": "secret_configured",
        "label": "API secret configured",
        "status": "SECURE" if api_key_set else "WARNING",
        "description": "An API key is configured." if api_key_set else
                       "No API key configured. Set SENTINEL_API_KEY in environment.",
    })

    from ai.dispatch_service import dispatch_status
    from ai.location_service import location_status
    dispatch = dispatch_status()
    location = location_status()
    checks.append({
        "key": "dispatch_provider",
        "label": "Dispatch provider",
        "status": "SECURE" if dispatch["safe_simulation"] else "WARNING",
        "description": f"Dispatch mode: {dispatch['mode']}. {dispatch['description']}.",
    })
    checks.append({
        "key": "gps_provider",
        "label": "GPS provider",
        "status": "SECURE" if location["mode"] in {"simulation", "manual"} else "WARNING",
        "description": f"GPS mode: {location['mode']}. Coordinates remain unavailable until a provider supplies them.",
    })

    # 3. Debug mode
    debug = bool(os.getenv("DEBUG", "").lower() in ("1", "true", "yes")) or os.getenv("DEV", "").lower() in ("1", "true", "yes")
    checks.append({
        "key": "debug_mode",
        "label": "Debug mode",
        "status": "WARNING" if debug else "SECURE",
        "description": "Debug mode is enabled." if debug else "Debug mode is disabled.",
    })

    # 4. CORS
    cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not cors_origins:
        cors_status = "WARNING"
        cors_desc = "CORS is open to all origins. Restrict to known frontends in production."
    else:
        cors_status = "SECURE"
        cors_desc = "CORS is restricted to specific origins."
    checks.append({
        "key": "cors_restricted",
        "label": "CORS configuration",
        "status": cors_status,
        "description": cors_desc,
    })

    # 5. Environment
    env = os.getenv("ENV", "production").lower()
    env_ok = env in ("production", "prod", "staging")
    checks.append({
        "key": "environment",
        "label": "Environment",
        "status": "SECURE" if env_ok else "WARNING",
        "description": f"Running in {env} mode.",
    })

    # 6. Database file permissions
    db_path = os.getenv("SENTINELAI_DB", "")
    checks.append({
        "key": "database",
        "label": "Database path",
        "status": "SECURE" if db_path else "WARNING",
        "description": f"Database: {db_path}" if db_path else "Using default database path.",
    })

    # 7. WebSocket
    checks.append({
        "key": "websocket",
        "label": "WebSocket security",
        "status": "SECURE",
        "description": "WebSocket endpoint /ws/alerts accepts same-origin connections.",
    })

    # 8. Audit log retention
    retention = int(os.getenv("AUDIT_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)))
    checks.append({
        "key": "audit_retention",
        "label": "Audit retention",
        "status": "SECURE" if retention >= 7 else "WARNING",
        "description": f"Audit retention is configured for {retention} days. (auto-prune not enabled)",
    })

    return {
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# Security health score
# ============================================================

def compute_security_score() -> dict[str, Any]:
    """Compute a 0-100 security health score.

    Factors:
      - Active security alerts (CRITICAL=−20, HIGH=−10, MEDIUM=−5, LOW=−2)
      - Recent failed requests
      - Configuration status
      - Backend health (always ONLINE in this build)
      - Total resolved alerts (positive)
    """
    try:
        alerts = list_security_alerts(limit=200)["alerts"]
        active_alerts = [a for a in alerts if a.get("status") == "ACTIVE"]
        resolved = [a for a in alerts if a.get("status") == "RESOLVED"]

        score = 100
        factors: list[dict[str, Any]] = []

        # Alerts deduction
        severity_penalty = {"CRITICAL": 20, "HIGH": 10, "MEDIUM": 5, "LOW": 2}
        for a in active_alerts:
            sev = a.get("severity", "LOW")
            score -= severity_penalty.get(sev, 2)
            factors.append({
                "factor": f"active_alert_{sev.lower()}",
                "delta": -severity_penalty.get(sev, 2),
                "reason": a.get("reason", "")[:80],
            })

        # Configuration penalty
        config = get_configuration_status()
        for c in config["checks"]:
            if c["status"] == "CRITICAL":
                score -= 15
                factors.append({"factor": f"config_{c['key']}", "delta": -15, "reason": c["label"]})
            elif c["status"] == "WARNING":
                score -= 5
                factors.append({"factor": f"config_{c['key']}", "delta": -5, "reason": c["label"]})

        # Positive: resolved alerts (each +1, capped +5)
        resolved_bonus = min(5, len(resolved))
        score += resolved_bonus
        if resolved_bonus:
            factors.append({"factor": "resolved_alerts", "delta": resolved_bonus, "reason": f"{len(resolved)} alert(s) resolved"})

        score = max(0, min(100, score))

        if score >= 80:
            category = "SECURE"
        elif score >= 50:
            category = "WARNING"
        else:
            category = "CRITICAL"

        return {
            "score": score,
            "category": category,
            "factors": factors,
            "active_alerts": len(active_alerts),
            "resolved_alerts": len(resolved),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"score": 50, "category": "WARNING", "factors": [{"factor": "compute_error", "delta": 0, "reason": str(e)}]}


# ============================================================
# Security overview (one-shot dashboard)
# ============================================================

def get_security_overview() -> dict[str, Any]:
    """One-shot security overview for the Security Center dashboard."""
    try:
        audit = query_audit(limit=20)
        alerts = list_security_alerts(limit=20)
        score = compute_security_score()
        config = get_configuration_status()

        # Tally audit stats
        by_type = audit["stats"].get("by_type", {})
        by_user = audit["stats"].get("by_user", {})
        failed = by_type.get(AUDIT_API_REQUEST_FAILED, 0) + by_type.get(AUDIT_LOGIN_FAILED, 0)

        # Active sessions (LOGIN events in last 24h not yet logged out)
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT user_id, MAX(timestamp) AS last_seen
                       FROM audit_events
                       WHERE timestamp >= ?
                       GROUP BY user_id""",
                    (cutoff,),
                )
                sessions = []
                for r in cursor.fetchall():
                    sessions.append({
                        "user_id": r["user_id"],
                        "last_seen": r["last_seen"],
                    })
        except Exception:
            sessions = []

        return {
            "score": score,
            "configuration": config,
            "audit_summary": {
                "total": audit["total"],
                "by_type": by_type,
                "by_user": by_user,
                "recent": audit["events"][:10],
                "failed_count": failed,
            },
            "alerts_summary": {
                "total": alerts["total"],
                "active": len([a for a in alerts["alerts"] if a["status"] == "ACTIVE"]),
                "resolved": len([a for a in alerts["alerts"] if a["status"] == "RESOLVED"]),
                "by_severity": {
                    "CRITICAL": len([a for a in alerts["alerts"] if a["severity"] == "CRITICAL"]),
                    "HIGH": len([a for a in alerts["alerts"] if a["severity"] == "HIGH"]),
                    "MEDIUM": len([a for a in alerts["alerts"] if a["severity"] == "MEDIUM"]),
                    "LOW": len([a for a in alerts["alerts"] if a["severity"] == "LOW"]),
                },
                "recent": alerts["alerts"][:10],
            },
            "active_sessions": sessions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "score": {"score": 50, "category": "WARNING"},
            "configuration": {"checks": []},
            "audit_summary": {"total": 0, "by_type": {}, "by_user": {}, "recent": [], "failed_count": 0},
            "alerts_summary": {"total": 0, "active": 0, "resolved": 0, "by_severity": {}, "recent": []},
            "active_sessions": [],
            "error": str(e),
        }


# ============================================================
# Retention helper (not auto-applied)
# ============================================================

def apply_retention(retention_days: int | None = None) -> dict[str, Any]:
    """Delete audit events older than retention_days. NOT auto-called.

    Caller must opt in explicitly. Returns the count of deleted rows.
    """
    days = int(retention_days or DEFAULT_RETENTION_DAYS)
    if days <= 0:
        return {"deleted": 0, "retention_days": days, "applied": False}
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
        return {"deleted": deleted, "retention_days": days, "applied": True, "cutoff": cutoff}
    except Exception as e:
        return {"deleted": 0, "retention_days": days, "applied": False, "error": str(e)}


# ============================================================
# Helpers
# ============================================================

def _safe_json_loads(s):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def extract_source_ip(request) -> str | None:
    """Extract a reasonable source IP from a FastAPI Request."""
    try:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else None
    except Exception:
        return None
