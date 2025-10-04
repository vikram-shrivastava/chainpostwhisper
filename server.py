from fastapi import FastAPI, UploadFile
import whisper
import shutil
import os

app = FastAPI()
model = whisper.load_model("base")

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    # save uploaded file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # run whisper transcription
    result = model.transcribe(temp_path)

    # generate .srt file
    srt_path = temp_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], start=1):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()

            # convert to SRT time format
            def format_time(seconds: float):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                ms = int((seconds % 1) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"

            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(f"{text}\n\n")

    # cleanup uploaded video immediately
    os.remove(temp_path)

    # read srt content into memory and delete the file
    with open(srt_path, "r", encoding="utf-8") as f:
        srt_content = f.read()
    os.remove(srt_path)  # delete srt file after reading

    # return JSON with transcript and SRT content
    return {
        "captions": result["text"],  # full transcript as plain text
        "srt": srt_content            # .srt formatted captions
    }
