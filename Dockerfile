# Use a lightweight Python base image
FROM docker.io/astral/uv:python3.12-bookworm-slim

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

# Copy the entire project into the container
COPY . .
RUN uv sync
# Expose the port your FastAPI/Uvicorn server listens on (adjust if needed)
EXPOSE 8000

# Command to run your MCP server
CMD ["uv", "run", "togo-mcp-server"]