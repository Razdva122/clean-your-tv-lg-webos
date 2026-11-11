FROM node:22-bookworm@sha256:539d4d5b9c0df96bb9d1229264d358dc816e8592cb8867828a580b527e7ad0fa AS node
FROM ubuntu:24.04@sha256:78d4744ead1f5b19b04d0df558ab182a5300903900755e515b2ca4d10eb2044d
ARG PLAYWRIGHT_VERSION
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers \
    PLAYWRIGHT_IMAGE_VERSION=${PLAYWRIGHT_VERSION} \
    PATH=/opt/ci-python/bin:$PATH
LABEL org.opencontainers.image.source="https://github.com/Razdva122/clean-your-tv-lg-webos"
COPY --from=node /usr/local/ /usr/local/
COPY --from=node /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
# Keep Noble suites and their Ubuntu signing keyring; avoid the default mirrors.
RUN sed -i 's|^URIs: .*|URIs: https://mirrors.edge.kernel.org/ubuntu|' /etc/apt/sources.list.d/ubuntu.sources \
    && printf 'Acquire::Retries "3";\nAPT::Update::Error-Mode "any";\n' > /etc/apt/apt.conf.d/80-ci-retries \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl gh git gcc g++ libatomic1 python3.12 python3.12-venv \
      qemu-user libc6-armel-cross libgcc-s1-armel-cross \
      fontconfig fonts-dejavu-core fonts-liberation fonts-noto-color-emoji \
    && python3.12 -m venv /opt/ci-python \
    && npm install --prefix /opt/ci-playwright --no-audit --no-fund --ignore-scripts "playwright@${PLAYWRIGHT_VERSION}" \
    && DEBIAN_FRONTEND=noninteractive /opt/ci-playwright/node_modules/.bin/playwright install --with-deps chromium firefox \
    && rm -rf /var/lib/apt/lists/* \
    && npm cache clean --force
