# syntax=docker/dockerfile:1.7
# Smoke-test build of OpenCEX-backend. Same as the backend repo's Dockerfile, plus:
#  - optional BuildKit secret "ca" (only needed behind a TLS-intercepting proxy; absent on a normal VPS)
#  - python:3.8-bookworm pinned instead of the floating python:3.8 tag
FROM python:3.8-bookworm
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /tmp/
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    python -m pip install "pip<24.1" && \
    pip install --no-cache-dir -r /tmp/requirements.txt
# upstream also apt-installs systemd (useless in a container) and gettext (only for `manage.py compilemessages`).
# Optional here because deb.debian.org is blocked in the sandbox: build with --build-arg APT_PACKAGES= to skip.
ARG APT_PACKAGES=gettext
RUN if [ -n "$APT_PACKAGES" ]; then apt-get update && apt-get install -y --no-install-recommends $APT_PACKAGES && rm -rf /var/lib/apt/lists/*; fi
