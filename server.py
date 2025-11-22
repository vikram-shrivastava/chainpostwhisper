# worker.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import tempfile
import os
from faster_whisper import WhisperModel  # type: ignore # Use faster-whisper for CPU-friendly processing

app = FastAPI()

# Load tiny model once at startup
model = WhisperModel("tiny", device="cpu", compute_type="int8")

NEXTJS_CALLBACK_URL = os.environ.get("NEXTJS_CALLBACK_URL")  # Example: https://your-nextjs-app/api/caption-result

class QStashMessage(BaseModel):
    CloudinaryURL: str
    PublicId: str
    OriginalSize: int
    userId: str

def format_time(seconds: float):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def process_video(video_url: str, public_id: str, original_size: int, user_id: str,project_id:str,platform:str):
    # Download video
    response = requests.get(video_url, stream=True)
    if response.status_code != 200:
        print("Failed to download video:", video_url)
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
        temp_path = temp_file.name

    # Transcribe using faster-whisper
    segments, info = model.transcribe(temp_path)
    transcription = " ".join([seg.text for seg in segments])

    # Generate SRT
    srt_path = temp_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg.start)} --> {format_time(seg.end)}\n")
            f.write(f"{seg.text.strip()}\n\n")

    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    # Cleanup
    os.remove(temp_path)
    os.remove(srt_path)

    # Send transcription result back to Next.js
    payload = {
        "captions": transcription,
        "srt": srt_content,
        "PublicId": public_id,
        "OriginalSize": original_size,
        "userId": user_id,
        "projectId":project_id,
        "platform":platform
    }

    if not NEXTJS_CALLBACK_URL:
        print("⚠️ NEXTJS_CALLBACK_URL not set; skipping callback.")
        return

    try:
        resp = requests.post(NEXTJS_CALLBACK_URL, json=payload, timeout=120)
        print("✅ Sent result to Next.js:", resp.status_code)
    except Exception as e:
        print("❌ Failed to send result:", e)


@app.post("/qstash-webhook")
async def qstash_webhook(request: Request):
    """
    This endpoint is called by QStash whenever a new job is published.
    """
    body = await request.json()
    print("🔥 Received QStash message:", body)

    # Validate keys
    for key in ["CloudinaryURL", "PublicId", "OriginalSize", "userId","projectId","platform"]:
        if key not in body:
            return {"status": "error", "message": f"{key} missing in payload"}

    # Process video synchronously
    process_video(
        video_url=body["CloudinaryURL"],
        public_id=body["PublicId"],
        original_size=body["OriginalSize"],
        user_id=body["userId"],
        project_id=body["projectId"],
        platform=body["platform"]
    )

    return {"status": "ok", "message": "Job processed"}
