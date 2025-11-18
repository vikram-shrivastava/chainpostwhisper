from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import whisper
import requests
import tempfile
import os
# use requests instead of httpx to avoid adding a new dependency

app = FastAPI()

# Load tiny model (fits under 512MB RAM)
model = whisper.load_model("tiny")

NEXTJS_CALLBACK_URL = "http://localhost:3000/api/caption-result"  # Next.js callback

class VideoURL(BaseModel):
    url: str
    PublicId: str
    OriginalSize: int
    userId: str

def format_time(seconds: float):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def process_video(video_url: str, public_id: str, original_size: int, user_id: str):
    # Download video
    response = requests.get(video_url, stream=True)
    if response.status_code != 200:
        print("Failed to download video:", video_url)
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_path = temp_file.name

    # Transcribe video
    result = model.transcribe(temp_path)

    # Generate .srt
    srt_path = temp_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result.get("segments", []), start=1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text'].strip()}\n\n")

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    os.remove(temp_path)
    os.remove(srt_path)

    # POST result to Next.js backend
    payload = {
        "captions": result.get("text", ""),
        "srt": srt_content,
        "PublicId": public_id,
        "OriginalSize": original_size,
        "userId": user_id
    }

    try:
        resp = requests.post(NEXTJS_CALLBACK_URL, json=payload, timeout=60)
        print("Sent result to Next.js:", resp.status_code, resp.text)
    except Exception as e:
        print("Failed to send result:", e)

@app.post("/transcribe")
async def transcribe(video: VideoURL, background_tasks: BackgroundTasks):
    # Queue background task
    background_tasks.add_task(process_video, video.url, video.PublicId, video.OriginalSize, video.userId)
    return {"status": "processing", "message": "Video is being transcribed in the background"}
