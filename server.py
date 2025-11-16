from fastapi import FastAPI
from pydantic import BaseModel
import whisper
import requests
import tempfile
import os

app = FastAPI()

# Load the tiny model to fit under 512MB RAM
model = whisper.load_model("tiny")

class VideoURL(BaseModel):
    url: str

@app.post("/transcribe")
async def transcribe(video: VideoURL):
    # Download video in streaming mode to save memory
    response = requests.get(video.url, stream=True)
    if response.status_code != 200:
        return {"error": "Failed to download video"}

    # Save video to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_path = temp_file.name

    # Transcribe with tiny model
    result = model.transcribe(temp_path)

    # Generate .srt file
    srt_path = temp_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result.get("segments", []), start=1):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()

            def format_time(seconds: float):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                ms = int((seconds % 1) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"

            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")

    # Cleanup video file
    os.remove(temp_path)

    # Read SRT content
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    os.remove(srt_path)

    return {
        "captions": result.get("text", ""),
        "srt": srt_content
    }
