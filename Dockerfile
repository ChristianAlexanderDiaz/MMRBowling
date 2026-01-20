# =============================================================================
# MMR Bowling Bot - Railway Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal for Discord bot + PostgreSQL)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application
COPY . .

# Run the bot
CMD ["python", "bot.py"]
