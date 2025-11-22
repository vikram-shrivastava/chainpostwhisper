# 1. Use Python 3.10 slim
FROM python:3.10-slim

# 2. Install system dependencies
# We add 'pkg-config', 'gcc', and 'libav*-dev' libraries.
# These are CRITICAL for compiling the 'av' library if a binary wheel isn't found.
RUN apt-get update && apt-get install -y \
    ffmpeg \
    pkg-config \
    gcc \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set working directory
WORKDIR /app

# 4. Copy requirements
COPY requirements.txt .

# 5. Upgrade pip and install dependencies
# Upgrading pip increases the chance it finds a pre-compiled wheel instead of building from source
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Start the application
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-4000}"]