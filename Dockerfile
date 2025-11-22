# 1. Use a lightweight version of Python 3.10
FROM python:3.10-slim

# 2. Install FFmpeg (This fixes your "pkg-config" error)
# We also clean up the cache immediately to keep the image small
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. Set the folder inside the container where your app will live
WORKDIR /app

# 4. Copy requirements first (this makes re-building faster)
COPY requirements.txt .

# 5. Install Python libraries
RUN pip install -r requirements.txt

# 6. Copy the rest of your code into the container
COPY . .

# 7. Tell Render what command to run to start the app
# We use "sh -c" so that the $PORT variable is read correctly
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-4000}"]