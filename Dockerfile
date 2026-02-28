FROM python:3.11-slim

# Install ffmpeg (required for yt-dlp format merging)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Always upgrade yt-dlp to the very latest release at build time.
# YouTube's extraction layer changes constantly; a pinned version goes
# stale within days and re-triggers bot detection errors.
RUN pip install --no-cache-dir --upgrade yt-dlp

# Copy application code
COPY . .

# Expose port and start gunicorn
# - 2 workers × 4 threads = 8 concurrent requests (safe for a 512 MB container)
# - timeout 120s for large video extractions
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
