# Stage 1: build the React frontend
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API that also serves the built frontend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY --from=frontend /frontend/dist ./frontend/dist

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# Hosts like Render set $PORT and terminate HTTPS at a proxy in front of the container
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.web:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
