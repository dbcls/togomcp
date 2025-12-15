# Use a lightweight Python base image
FROM astral/uv:python3.12-bookworm-slim
# Set the working directory inside the container
WORKDIR /app

ENV TOGOMCP_DIR=/app

# Copy the entire project into the container
COPY . .
RUN uv sync
# Expose the port your FastAPI/Uvicorn server listens on (adjust if needed)
EXPOSE 8000

# Command to run your MCP server
CMD ["uv", "run", "togo-mcp-server"]