# Use a lightweight Python base image
FROM docker.io/astral/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

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