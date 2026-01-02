FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scriberr_gateway ./scriberr_gateway
COPY pyproject.toml README.md ./

ENV SCRIBERR_GATEWAY_CONFIG=/app/config.yaml

EXPOSE 8000

CMD ["uvicorn", "scriberr_gateway.server:app", "--host", "0.0.0.0", "--port", "8000"]
