FROM python:3.12-slim AS builder


RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev  \
        && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt



# ---------- Stage 2: runtime (final image) ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown appuser:appuser /app/staticfiles /app/media

USER appuser

EXPOSE 8000
ENTRYPOINT ["sh", "entrypoint.sh"]


