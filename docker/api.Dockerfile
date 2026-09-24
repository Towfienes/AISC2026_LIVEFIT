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
# Chỉ ba thứ này được COPY — .dockerignore ở gốc repo là danh sách cho phép khớp
# đúng ba dòng dưới (thêm COPY thì mở thêm ở đó). scikit-learn cài theo ghim
# "==" trong pyproject (phải khớp *.meta.json của artifact ý định — kiểm toán 25/09).
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir ".[server,ml]"

# Run as a non-root user.
# /app/data thuộc livelift (kiểm toán Docker 25/09/2026, docker.md P1-2): /app do
# root tạo nên user livelift không ghi được tệp trạng thái bộ thu
# (data/ingest-jobs.json) và spool (data/spool) — "tự nối lại bộ thu sau restart"
# chết âm thầm, chỉ để lại một dòng WARNING. docker-compose.yml gắn volume
# `appdata` vào đây để tệp sống qua `up --build`/`--force-recreate`; volume rỗng
# lần đầu được Docker chép quyền sở hữu từ chính thư mục này.
RUN useradd --create-home --uid 1000 livelift \
    && mkdir -p /app/data \
    && chown livelift:livelift /app/data
USER livelift

EXPOSE 8000
CMD ["uvicorn", "livelift.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
