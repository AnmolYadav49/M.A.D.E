# Container image for M.A.D.E.
#
# This exists mainly for the case the plain Python deploy cannot safely cover:
# running generated code (MADE_ALLOW_EXECUTION=1) on a host that strangers can
# reach. The AST audit is defence in depth, not a sandbox — so if execution is
# on, the process itself has to be the boundary. This image runs as a
# non-root user with no build toolchain, which is the minimum bar; deploy it
# with the runtime flags in the README's threat-model section (--network=none
# on the exec path, read-only rootfs, dropped capabilities).
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so application edits don't invalidate the wheel layer.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code. The built frontend is committed, so there is no Node stage.
COPY . .

# Build the FAISS methodology index at image build time. Non-fatal: the
# researcher falls back to unguided prompting when the index is absent, and
# failing the whole build over a model download would be worse.
RUN python build_db.py || echo "FAISS index build skipped"

# Drop privileges. Generated code, if execution is enabled, inherits this user —
# it must not be root.
RUN useradd --create-home --shell /usr/sbin/nologin made \
    && chown -R made:made /app
USER made

EXPOSE 8000

# Render/Fly/Railway inject $PORT; default to 8000 for plain `docker run`.
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
