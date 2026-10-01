# ── Frontend build ────────────────────────────────────────────────────────────
FROM node:24.19.0-alpine AS web-builder

WORKDIR /workspace/gaia-frontend

COPY gaia-frontend/package.json gaia-frontend/package-lock.json ./
RUN npm ci

COPY gaia-frontend/ ./
RUN npm run build

# ── Rust build ────────────────────────────────────────────────────────────────
FROM rust:1.95.0-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy workspace manifests first for layer caching
COPY Cargo.toml Cargo.lock ./
COPY gaia-protocol/Cargo.toml gaia-protocol/
COPY gaia-engine/Cargo.toml gaia-engine/
COPY gaia-server/Cargo.toml gaia-server/

# Create dummy lib/main to cache dependency compilation
RUN mkdir -p gaia-protocol/src gaia-engine/src gaia-server/src \
    && echo "pub fn dummy() {}" > gaia-protocol/src/lib.rs \
    && echo "pub fn dummy() {}" > gaia-engine/src/lib.rs \
    && echo "fn main() {}" > gaia-server/src/main.rs \
    && cargo build --release -p gaia-server \
    && rm -rf gaia-protocol/src gaia-engine/src gaia-server/src

# Copy real source
COPY gaia-protocol/src gaia-protocol/src
COPY gaia-engine/src gaia-engine/src
COPY gaia-engine/data gaia-engine/data
COPY gaia-server/src gaia-server/src
COPY gaia-server/migrations gaia-server/migrations

RUN touch gaia-protocol/src/lib.rs gaia-engine/src/lib.rs gaia-server/src/main.rs \
    && cargo build --release -p gaia-server

# ── AI worker: native game environment wheel for the Python teacher ──────────
FROM python:3.12-slim-bookworm AS ai-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain 1.95.0
ENV PATH=/root/.cargo/bin:$PATH
RUN pip install --no-cache-dir "maturin>=1.15,<2"

WORKDIR /workspace
COPY gaia-engine/Cargo.toml gaia-engine/
COPY gaia-engine/src gaia-engine/src
COPY gaia-engine/data gaia-engine/data
COPY gaia-rl/Cargo.toml gaia-rl/Cargo.lock gaia-rl/build.rs gaia-rl/pyproject.toml gaia-rl/
COPY gaia-rl/src gaia-rl/src
COPY gaia-rl/python gaia-rl/python
RUN cd gaia-rl && maturin build --release -i python3.12 --out /wheels

# ── Runtime stage ─────────────────────────────────────────────────────────────
# Python runtime (Debian bookworm) so the server can run its AI worker pool.
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /workspace/target/release/gaia-server ./gaia-server
COPY gaia-server/migrations ./migrations
COPY --from=web-builder /workspace/gaia-frontend/dist ./gaia-frontend/dist

# AI seats (gaia-server/src/ai.rs). The teacher finds its data relative to the repository
# root, so /opt/gaia mirrors the repository layout. Enable with GAIA_AI_DIR=/opt/gaia/gaia-rl.
COPY --from=ai-builder /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels
COPY gaia-rl/baseline-teacher-20260917 /opt/gaia/gaia-rl/baseline-teacher-20260917
COPY gaia-rl/tools/ai_worker.py gaia-rl/tools/fast_teacher.py gaia-rl/tools/fast_copy.py \
     gaia-rl/tools/budget_teacher.py /opt/gaia/gaia-rl/tools/
COPY gaia-rl/research/strategy/bgg-openings-part2.csv /opt/gaia/gaia-rl/research/strategy/
COPY gaia-frontend/src/data /opt/gaia/gaia-frontend/src/data
COPY gaia-engine/data /opt/gaia/gaia-engine/data
ENV GAIA_AI_PYTHON=/usr/local/bin/python3

EXPOSE 8080

ENTRYPOINT ["./gaia-server"]
