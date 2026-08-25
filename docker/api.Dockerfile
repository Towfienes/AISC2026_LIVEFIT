# LiveLift API image — FastAPI (uvicorn) + CLI entry points (livelift-migrate, ...).
# Build context: repository root (see docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1 is required at runtime by lightgbm wheels (OpenMP).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the package (src layout; SQL migrations ship inside src/livelift/migrations).
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[server,ml]"

# Run as a non-root user.
RUN useradd --create-home --uid 1000 livelift
USER livelift

EXPOSE 8000
CMD ["uvicorn", "livelift.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
