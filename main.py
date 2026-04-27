from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from faster_whisper import WhisperModel
import os
import tempfile
import shutil
import uvicorn
import requests
import time

app = FastAPI(title="Open Whisper Local API")

# Configuration
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

print(f"Loading Whisper model '{MODEL_SIZE}' on {DEVICE}...")
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("Model loaded successfully.")

class TranscribeRequest(BaseModel):
    appointment_id: str
    recording_url: str
    callback_url: str

@app.get("/")
async def root():
    return {
        "message": "Open Whisper API is running",
        "status": "active",
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)"
        }
    }

@app.get("/health")
@app.head("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE
    }

def run_transcription_task(request: TranscribeRequest):
    print(f"Starting background transcription for appointment: {request.appointment_id}", flush=True)
    tmp_path = None
    try:
        # 1. Download the file
        print(f"Downloading audio from: {request.recording_url}", flush=True)
        suffix = os.path.splitext(request.recording_url.split('?')[0])[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            response = requests.get(request.recording_url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # 2. Transcribe
        print(f"Transcribing audio (Model: {MODEL_SIZE})...", flush=True)
        start_time = time.time()
        segments, info = model.transcribe(tmp_path, beam_size=5)
        
        transcript = ""
        for segment in segments:
            transcript += segment.text + " "
        
        transcript = transcript.strip()
        elapsed = time.time() - start_time
        print(f"Transcription finished in {elapsed:.2f}s. Result: {transcript[:50]}...", flush=True)
        
        # 3. Call Callback
        callback_data = {
            "success": True,
            "appointmentId": request.appointment_id,
            "transcript": transcript,
            "duration": info.duration,
            "language": info.language
        }
        
        print(f"Sending callback to {request.callback_url}", flush=True)
        res = requests.post(request.callback_url, json=callback_data)
        res.raise_for_status()
        print(f"Callback successful for {request.appointment_id}", flush=True)

    except Exception as e:
        print(f"Background transcription failed for {request.appointment_id}: {e}")
        try:
            requests.post(request.callback_url, json={"success": false, "error": str(e)})
        except:
            pass
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/transcribe")
async def transcribe(
    background_tasks: BackgroundTasks,
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    # Check if it's a JSON request
    content_type = request.headers.get("Content-Type", "")
    
    if "application/json" in content_type:
        try:
            data = await request.json()
            request_data = TranscribeRequest(**data)
            background_tasks.add_task(run_transcription_task, request_data)
            return {"success": True, "message": "Transcription started in background"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")

    # Handle direct file upload (Sync - for testing)
    if file:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            segments, info = model.transcribe(tmp_path, beam_size=5)
            transcript = " ".join([s.text for s in segments]).strip()
            return {
                "text": transcript,
                "language": info.language,
                "duration": info.duration
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    raise HTTPException(status_code=400, detail="Either file (multipart/form-data) or recording_url (application/json) must be provided")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
