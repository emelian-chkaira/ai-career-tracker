# --- web build
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# --- API + worker image (the API serves the built web app from /app/frontend/dist)
FROM python:3.13-slim
ARG WITH_BROWSER=1
ENV PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright CAREERS_DATA_DIR=/data
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir -r backend/requirements.txt \
 && if [ "$WITH_BROWSER" = "1" ]; then playwright install --with-deps chromium; fi \
 && useradd -m app && mkdir -p /data && chown app /data
COPY backend backend
COPY CHANGELOG.md CHANGELOG.md
COPY --from=web /web/dist frontend/dist
# `demo` branch only: this image is the public online demo (feature tour, one-click guest accounts, no crawler-backed actions)
ENV CAREERS_DEMO_MODE=true
USER app
WORKDIR /app/backend
EXPOSE 8787
VOLUME /data
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:'+__import__('os').environ.get('PORT','8787')+'/healthz')" || exit 1
# PORT is set by hosts such as Render; CAREERS_SEED=0 skips loading the ready-made starter data (it only ever fills an empty database)
CMD ["sh","-c","alembic upgrade head && if [ \"${CAREERS_SEED:-1}\" = 1 ]; then python -m app.cli seed; fi && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8787} --proxy-headers"]
