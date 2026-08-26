# ==============================================================================
# Multi-Stage Build for Eth-Hunter (FastAPI + Foundry EVM Engine on Google Cloud Run)
# Fully Compatible with Google Cloud Free Tier (Cloud Run 2M requests/month)
# ==============================================================================

FROM ghcr.io/foundry-rs/foundry:nightly as foundry

FROM python:3.11-slim

# Copy forge and cast binaries from Foundry image
COPY --from=foundry /usr/local/bin/forge /usr/local/bin/forge
COPY --from=foundry /usr/local/bin/cast /usr/local/bin/cast

WORKDIR /app

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application source code
COPY backend ./backend
COPY contracts ./contracts
COPY foundry.toml ./foundry.toml

# Google Cloud Run injects PORT environment variable (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
