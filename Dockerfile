# Use official Python image
FROM python:3.13-slim-bookworm

# Set work directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock /_lock/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache \
    cd /_lock && \
    uv sync \
    --frozen \
    --no-install-project

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Default command
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]
