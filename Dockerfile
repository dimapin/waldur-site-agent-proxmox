ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION} AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

COPY pyproject.toml README.md ./
COPY waldur_site_agent_proxmox/ waldur_site_agent_proxmox/
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:${PYTHON_VERSION} AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin agent
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index \
        --find-links=/wheels waldur-site-agent-proxmox \
    && rm -rf /wheels

USER 10001
WORKDIR /home/agent

ENTRYPOINT ["waldur_site_agent"]
CMD ["--config-file", "/etc/waldur-site-agent/config.yaml"]

