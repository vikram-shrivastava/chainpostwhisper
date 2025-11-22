# 1. Use Debian Bullseye (older, stable Linux).
# This version has libraries that play nicely with 'av' and 'faster-whisper'.
FROM python:3.10-slim-bullseye

# 2. Install FFmpeg runtime (needed for the app to listen/speak)
# We don't need the complex '-dev' packages anymore.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 3. Set working directory
WORKDIR /app

# 4. Copy requirements
COPY requirements.txt .

# 5. Upgrade pip FIRST, then install requirements.
# This is crucial: It helps Docker find the pre-built "Wheel" files
# so it doesn't try (and fail) to build 'av' from scratch.
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Start the application
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-4000}"]