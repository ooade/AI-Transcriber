# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
# ffmpeg: required for audio processing
# libsndfile1: required for soundfile/librosa
# git: required for pip install git+...
# procps: required for monitoring processes
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    procps \
    curl \
    make \
    g++ \
    cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory for audio files
RUN mkdir -p temp

# Create a non-root user and switch to it
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
