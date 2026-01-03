# Scriberr Gateway - Technical Specification

## Purpose
Provide a lightweight HTTP gateway that forwards file uploads to Scriberr, triggers transcription runs, polls for completion, and sends results to Apprise.

## Service API
### `POST /upload`
- **Auth**: `x-api-key` header or `api_key` form field must match `security.api_key`.
- **Body**: multipart form with a `file` field.
- **Response**: the JSON response from Scriberr's upload endpoint.
- **Behavior**:
  1. Uploads the file to Scriberr.
  2. Returns Scriberr's response to the client.
  3. Starts a background workflow to trigger and monitor the run.

### `GET /health`
Simple liveness check.

## Background Workflow
1. Extract `id` from the upload response (also checks `query_id`, `request_id`, `run_id`).
2. If no cached JWT exists or it is too old, `POST {base_url}/api/v1/auth/login` with `{ "username": "...", "password": "..." }`.
3. Uploads and follow-up calls use `Authorization: Bearer <token>`.
4. `POST {base_url}/api/v1/transcription/{query_id}/start`.
5. Poll `GET {base_url}/api/v1/transcription/{run_id}` until the `status` (or `state`) matches a completion value from `processing.status_complete_values`.
6. If the status does not contain text, fetch `GET {base_url}/api/v1/transcription/{run_id}/transcript`.
7. Send the text via Apprise.

## Configuration
Configuration is loaded from `config.yaml` or `SCRIBERR_GATEWAY_CONFIG`.

```yaml
server:
  host: "0.0.0.0"
  port: 8000
security:
  api_key: "..."
scriberr:
  base_url: "..."
  username: "..."
  password: "..."
  token_cache_minutes: 30
apprise:
  url: "mailto://user:pass@example.com"
  tag: "scriberr"  # optional
processing:
  poll_interval_seconds: 10
  poll_timeout_seconds: 900
  status_complete_values:
    - "completed"
    - "done"
  status_failed_values:
    - "failed"
    - "error"
```

## Implementation Notes
- Module entrypoint: `scriberr_gateway.server:app`.
- Background execution uses `fastapi.BackgroundTasks`.
- HTTP calls are handled by `requests`.
- Apprise notifications are sent in `scriberr_gateway.notification`.

## Packaging
- `pyproject.toml` defines the package and dependencies.
- `requirements.txt` mirrors runtime dependencies.
- `Dockerfile` provides containerized deployment.
