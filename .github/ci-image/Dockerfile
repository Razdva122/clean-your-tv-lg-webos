FROM node:22-bookworm-slim@sha256:aaa4b5baf1ecff3b283486bb1f90405cdda225a3e6f79660d2c559fa510a7292 AS node
FROM ubuntu:24.04@sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d
ARG PLAYWRIGHT_VERSION
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers \
    PLAYWRIGHT_IMAGE_VERSION=${PLAYWRIGHT_VERSION} \
    PATH=/opt/ci-python/bin:$PATH
LABEL org.opencontainers.image.source="https://github.com/Razdva122/clean-your-tv-lg-webos"
COPY --from=node /usr/local/ /usr/local/
RUN apt-get update -o Acquire::Retries=3 \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl gh git gcc g++ libatomic1 python3.12 python3.12-venv \
      qemu-user libc6-armel-cross libgcc-s1-armel-cross \
      fontconfig fonts-dejavu-core fonts-liberation fonts-noto-color-emoji \
    && python3.12 -m venv /opt/ci-python \
    && npm install --prefix /opt/ci-playwright --no-audit --no-fund --ignore-scripts "playwright@${PLAYWRIGHT_VERSION}" \
    && DEBIAN_FRONTEND=noninteractive /opt/ci-playwright/node_modules/.bin/playwright install --with-deps chromium firefox \
    && rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force
