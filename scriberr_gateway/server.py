from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

from .config import DEFAULT_CONFIG_PATH, AppConfig, ConfigError, load_config
from .notification import send_notification
from .scriberr_client import ScriberrError, fetch_text, poll_run, trigger_run, upload_file

logger = logging.getLogger("scriberr_gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CONFIG_PATH_ENV = "SCRIBERR_GATEWAY_CONFIG"

app = FastAPI(title="Scriberr Gateway", version="0.2.0")

_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        path = os.getenv(CONFIG_PATH_ENV) or DEFAULT_CONFIG_PATH
        try:
            _config = load_config(path)
        except ConfigError as exc:
            logger.error("Config error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _config


def _resolve_api_key(api_key: str | None, header_key: str | None) -> str | None:
    if api_key:
        return api_key
    if header_key:
        return header_key
    return None


def _extract_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "query_id", "request_id", "run_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _process_run(config: AppConfig, query_id: str) -> None:
    try:
        run_response = trigger_run(config.scriberr, query_id)
        run_id = _extract_id(run_response) or query_id

        status_response = poll_run(config.scriberr, config.processing, run_id)
        text = status_response.get("text")
        text = fetch_text(config.scriberr, run_id)
        
        send_notification(
            config.apprise,
            title=f"Scriberr run {run_id} completed",
            body=text,
        )
    except ScriberrError as exc:
        logger.error("Scriberr processing failed: %s", exc)
        send_notification(
            config.apprise,
            title="Scriberr run failed",
            body=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during background processing")
        send_notification(
            config.apprise,
            title="Scriberr run failed",
            body=str(exc),
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str | None = Form(None),
    x_api_key: str | None = Header(None),
    config: AppConfig = Depends(get_config),
) -> dict[str, Any]:
    provided_key = _resolve_api_key(api_key, x_api_key)
    if not provided_key or provided_key != config.security.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        upload_response = upload_file(config.scriberr, file_bytes, file.filename)
    except ScriberrError as exc:
        if exc.status_code:
            detail = exc.payload if exc.payload is not None else str(exc)
            raise HTTPException(status_code=exc.status_code, detail=detail) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload to Scriberr failed")
        raise HTTPException(status_code=502, detail="Upload to Scriberr failed") from exc

    query_id = _extract_id(upload_response)
    if query_id:
        background_tasks.add_task(_process_run, config, query_id)

    return upload_response


def run() -> None:
    import uvicorn

    config_path = os.getenv(CONFIG_PATH_ENV) or DEFAULT_CONFIG_PATH
    config = load_config(config_path)
    uvicorn.run(
        "scriberr_gateway.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=False,
    )
