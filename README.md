# Scriberr Gateway

A lightweight Python service that forwards file uploads to Scriberr, triggers processing, polls for completion, and sends the resulting text to Apprise.

## Quick start
```bash
cp config.example.yaml config.yaml
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn scriberr_gateway.server:app --reload --host 0.0.0.0 --port 8000
```

## Documentation
- [End User Guide](docs/END_USER.md)
- [Technical Specification](docs/TECHNICAL_SPEC.md)
