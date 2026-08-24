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

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /workspace/target/release/gaia-server ./gaia-server
COPY gaia-server/migrations ./migrations
COPY --from=web-builder /workspace/gaia-frontend/dist ./gaia-frontend/dist

EXPOSE 8080

ENTRYPOINT ["./gaia-server"]
