FROM python:3.12-slim

# - PYTHONUNBUFFERED: stream logs straight to stdout (no buffering) so the JSON
#   logger's output shows up immediately in `docker logs`.
# - PYTHONDONTWRITEBYTECODE: don't litter the (bind-mounted) source tree with
#   .pyc files and avoid write-permission issues when running as non-root.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first so the layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user in production.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness check used by orchestrators / compose. Uses the stdlib so no extra
# package (curl) is needed in the slim image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else sys.exit(1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
