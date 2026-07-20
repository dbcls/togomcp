# Use a lightweight Python base image.
# Pinned by digest for reproducible builds — bump the digest to move Python/uv/OS.
# python3.12-trixie-slim (Debian 13) = Python 3.12.13, uv 0.11.28 (image built 2026-07-07).
# NB: astral froze the bookworm-slim (Debian 12) line at uv 0.9.30 / Python 3.12.12
# on 2026-02-04 and now ships only trixie variants, so this is a Debian 12->13 bump.
FROM docker.io/astral/uv:python3.12-trixie-slim@sha256:36cdfbf910c8b0f651355c013e7ece9678f4ecbf030a9fd9e6779de421189805

# Install tzdata so the TZ env var (set in compose.yaml) resolves correctly
# instead of silently falling back to UTC.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Data files are bundled inside the togo_mcp package at togo_mcp/data/.
# Set TOGOMCP_DIR only if you need to override with external data.
# ENV TOGOMCP_DIR=/app/togo_mcp/data

# Install dependencies FIRST, in a layer keyed only on the lockfiles. This stays
# cached across source-only changes — COPY . . below busts the project-install
# layer, not this dependency layer, so deps don't reinstall on every code edit.
# --frozen: install exactly what uv.lock pins; fail the build if the lock is
# stale vs pyproject.toml instead of silently re-resolving to newer versions.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy the rest of the project, then install the package itself.
COPY . .
RUN uv sync --frozen
# Expose the port your FastAPI/Uvicorn server listens on (adjust if needed)
EXPOSE 8000

# Command to run your MCP server
CMD ["uv", "run", "--frozen", "togo-mcp-server"]