# Emergency Response

SentinelAI's Emergency Response module is an operational layer over existing HIGH and CRITICAL incidents. It uses the existing incident ID as the unique source reference and never creates a second incident record.

## Workflow

`PENDING -> ACKNOWLEDGED -> DISPATCH_RECOMMENDED -> DISPATCHED -> RESPONDING -> ON_SCENE -> RESOLVED`

An active case may also be `CANCELLED`. Invalid transitions are rejected by the backend. Cases are created idempotently from serious incidents, both through `POST /api/emergency-responses` and automatically when the detection pipeline creates a serious incident.

## Severity and scoring

The backend uses a transparent rule-based score. It combines the existing incident risk score, incident severity, accident/collision indicators, vulnerable road user indicators, detected object count, and traffic-density metadata when present. The score is normalized to 0-100 and mapped to LOW, MEDIUM, HIGH, or CRITICAL. Priority maps to P4, P3, P2, or P1 respectively. No new ML model or detector class is introduced.

## API

- `GET /api/emergency-responses`
- `POST /api/emergency-responses`
- `GET /api/emergency-responses/{id}`
- `PATCH /api/emergency-responses/{id}/status`
- `POST /api/emergency-responses/{id}/acknowledge`
- `POST /api/emergency-responses/{id}/escalate`
- `POST /api/emergency-responses/{id}/assign-unit`
- `POST /api/emergency-responses/{id}/reassign-unit`
- `POST /api/emergency-responses/{id}/note`
- `POST /api/emergency-responses/{id}/resolve`
- `GET /api/emergency-responses/{id}/timeline`
- `GET /api/emergency-responses/{id}/recommendations`
- `GET /api/emergency-units`
- `POST /api/emergency-units`
- `PATCH /api/emergency-units/{id}`
- `GET /api/emergency-response/analytics`

## Persistence and realtime

SQLite tables are initialized by `backend/ai/emergency_service.py`: `emergency_responses`, `emergency_response_events`, `emergency_units`, `emergency_assignments`, and `emergency_notes`. Important actions are written through the existing Security & Audit Center. Realtime updates use the existing singleton `/ws/alerts` connection with `type: emergency_response` events.

## Units and limitations

The default response units are clearly named `Simulated ...` and use `Location metadata unavailable`. They are not real dispatch resources and no emergency service is contacted. Unit assignment is guarded against unavailable units and duplicate active assignments. Real GPS, dispatch, authentication middleware, and external emergency integrations are not present in the current project, so the module remains an auditable simulation.

## Frontend

Open `/emergency-response`. The page provides the queue, severity factors, response timeline, recommendations, simulated unit assignment, notes, incident/investigation/camera links, status actions, realtime connection state, and persisted response metrics.
