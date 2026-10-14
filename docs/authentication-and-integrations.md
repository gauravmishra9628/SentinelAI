# Authentication and Integration Safety

## Authentication

Set `AUTH_ENABLED=true` and provide `SENTINEL_AUTH_SECRET` with at least 32 random characters. Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes. The first administrator is created only when `SENTINEL_BOOTSTRAP_ADMIN_PASSWORD` is explicitly set in the server environment; remove or rotate the bootstrap value after setup.

Login is `POST /api/auth/login` with `{ "username": "...", "password": "..." }`. The response contains a bearer access token. Protected API requests require `Authorization: Bearer <token>`. `ADMIN`, `OPERATOR`, and `VIEWER` roles are enforced by backend middleware; missing or invalid credentials return 401 and insufficient roles return 403.

`GET /api/health` and the root status endpoint remain public. User creation and role changes are administrator-only. Existing read workflows require an authenticated viewer or higher; mutations require an operator or administrator unless explicitly administrator-only.

## Location and dispatch

`GPS_MODE=simulation` and `DISPATCH_MODE=simulation` are the safe defaults. Location records use `CAMERA`, `GPS`, `MANUAL`, `SIMULATED`, or `UNAVAILABLE` sources. The current simulated provider intentionally returns no precise coordinates. The simulation dispatch provider changes local response/unit state only and never contacts emergency services.

The provider interfaces are in `backend/ai/location_service.py` and `backend/ai/dispatch_service.py`. Future GPS or external dispatch implementations can replace the providers without changing Emergency Response orchestration.

## Frontend

The React shell provides `/login`, stores the access token in browser local storage for the current single-page application, attaches it to Axios and the existing singleton WebSocket, and reacts to 401 expiry events. The backend remains authoritative for role enforcement.
