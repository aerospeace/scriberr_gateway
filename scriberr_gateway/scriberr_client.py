from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from .config import ProcessingConfig, ScriberrConfig


class ScriberrError(RuntimeError):
    pass


@dataclass
class ScriberrResult:
    upload_response: dict[str, Any]
    run_id: str | None
    text: str | None


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _extract_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "query_id", "request_id", "run_id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _extract_text(payload: dict[str, Any]) -> str | None:
    for key in ("text", "transcript", "result", "output"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def upload_file(config: ScriberrConfig, file_bytes: bytes, filename: str) -> dict[str, Any]:
    url = f"{config.base_url}/api/v1/transcription/upload"
    headers = {"X-API-Key": config.api_key}
    files = {"audio": (filename, file_bytes)}
    # Extract filename without extension for the title
    base_title = os.path.splitext(filename)[0]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    title = f"{base_title}_{timestamp}"
    data = {"title": title}

    response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    response.raise_for_status()
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise ScriberrError("Upload response did not contain JSON") from exc
    

def trigger_run(config: ScriberrConfig, query_id: str) -> dict[str, Any]:
    url = f"{config.base_url}/api/v1/transcription/{query_id}/start"
    headers = {
        "X-API-Key": config.api_key,
        "Content-Type": "application/json",
    }
    # payload = {"id": query_id}
    # response = requests.post(url, headers=headers, json=payload, timeout=60)
    response = requests.post(url, headers=headers, timeout=60)
    response.raise_for_status()
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise ScriberrError("Run response did not contain JSON") from exc


def poll_run(
    config: ScriberrConfig,
    processing: ProcessingConfig,
    id: str,
) -> dict[str, Any]:
    url = f"{config.base_url}/api/v1/transcription/{id}"
    headers = {"X-API-Key": config.api_key}

    start_time = time.time()
    while True:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        status = _normalize_status(data.get("status") or data.get("state"))
        if status in processing.status_complete_values:
            return data
        if status in processing.status_failed_values:
            raise ScriberrError(f"Run failed with status '{status}'")

        if time.time() - start_time > processing.poll_timeout_seconds:
            raise ScriberrError("Polling timed out waiting for Scriberr run")

        time.sleep(processing.poll_interval_seconds)


def fetch_text(config: ScriberrConfig, id: str) -> dict[str, Any]:
    url = f"{config.base_url}/api/v1/transcription/{id}/transcript"
    headers = {"X-API-Key": config.api_key}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    json = response.json()
    return json["transcript"]["text"]


def process_upload(
    config: ScriberrConfig,
    processing: ProcessingConfig,
    file_bytes: bytes,
    filename: str,
) -> ScriberrResult:
    upload_response = upload_file(config, file_bytes, filename)
    id = _extract_id(upload_response)
    if not id:
        raise ScriberrError("Upload response did not include an id field")

    status_response = poll_run(config, processing, id)
    text = _extract_text(status_response)
    if text:
        return ScriberrResult(upload_response, id, text)

    text_response = fetch_text(config, id)
    return ScriberrResult(upload_response, id, _extract_text(text_response))
