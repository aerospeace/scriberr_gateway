# Scriberr Gateway - End User Guide

## Overview
This service accepts file uploads over HTTP, forwards them to your Scriberr instance, waits for processing to finish, and sends the final text through Apprise. It supports deployment via Docker or `pip install`.

## Prerequisites
- A Scriberr instance reachable at your URL
- A Scriberr username and password.
- An Apprise notification URL (email, Discord, Slack, etc.).

## Configuration
1. Copy the example file:
   ```bash
   cp config.example.yaml config.yaml
   ```
2. Edit `config.yaml`:
   - `security.api_key`: the API key that clients must provide when calling `/upload`.
   - `scriberr.base_url`: base URL of your Scriberr instance.
   - `scriberr.username`: Scriberr username.
   - `scriberr.password`: Scriberr password.
   - `scriberr.token_cache_minutes`: number of minutes to cache the Scriberr JWT in memory.
   - `apprise.url`: Apprise target URL.
   - Optional `apprise.tag`: tag for Apprise notifications.

## Run locally with pip
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
uvicorn scriberr_gateway.server:app --reload --host 0.0.0.0 --port 8000
```

## Run with Docker
```bash
docker build -t scriberr-gateway .
docker run --rm -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  scriberr-gateway
```

## Upload a file
The service expects a multipart form with a file and the API key.

```bash
curl -X POST http://localhost:8000/upload \
  -H "x-api-key: YOUR_GATEWAY_KEY" \
  -F "file=@/path/to/audio.wav"
```

The API immediately returns the Scriberr upload response. Processing continues in the background and sends the final text to Apprise once ready.

## Health check
```bash
curl http://localhost:8000/health
```
