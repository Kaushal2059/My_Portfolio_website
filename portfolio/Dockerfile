# Multi-stage build for the portfolio Django app.
#   Stage 1 (builder): has compilers, installs the Python packages into /opt/venv.
#   Stage 2 (runtime): clean slim image that only receives /opt/venv + the app code.
# Only the last stage becomes the final image, so gcc/libpq-dev never ship.
# Both stages MUST use the same base image: the venv is tied to /usr/local/bin/python 3.12.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

# Build tools, only needed if a package has no ready-made wheel and must be compiled.
# --no-install-recommends keeps the install minimal; the apt index is deleted in the
# same RUN so it is never saved into a layer.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev  \
        && rm -rf /var/lib/apt/lists/*

# Install everything into one virtual env so the runtime stage can copy it in one line.
# ENV (not "activate") because every RUN is a new shell; PATH makes pip/python = the venv's.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
# requirements.txt first: the slow pip install layer stays cached when only code changes.
COPY requirements.txt .
# --no-cache-dir: don't keep pip's download cache in the layer.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt



# ---------- Stage 2: runtime (final image) ----------
# Fresh start: nothing from the builder exists here unless copied with COPY --from.
FROM python:3.12-slim

# ENV does not carry over between stages, so PATH must point at the venv again,
# otherwise entrypoint.sh would run the system python/gunicorn (no packages installed).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user for running the app. Fixed UID so volume file ownership stays the
# same across rebuilds; --create-home because gunicorn writes ~/.gunicorn/.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# The finished venv from the builder (psycopg2-binary bundles its own libpq,
# so no apt packages are needed in this stage).
COPY --from=builder /opt/venv /opt/venv
COPY . .

# The only folders the app writes to: collectstatic output and user uploads.
# They are excluded by .dockerignore, so create them and hand them to appuser.
# Everything else (code, venv) stays root-owned = read-only for the app.
# A NEW empty named volume mounted here copies this ownership; old root-owned
# volumes do not change and must be recreated.
RUN mkdir -p /app/staticfiles /app/media \
    && chown appuser:appuser /app/staticfiles /app/media

# Everything below, and the running container, uses appuser instead of root.
USER appuser

EXPOSE 8000
# entrypoint.sh: migrate -> collectstatic -> gunicorn. Needs LF line endings
# (CRLF from a Windows checkout gives "set: Illegal option -").
ENTRYPOINT ["sh", "entrypoint.sh"]
