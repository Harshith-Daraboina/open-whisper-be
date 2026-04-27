---
title: Open Whisper BE
emoji: 🎙️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Open Whisper Local API (Hugging Face Edition)

This is a local Whisper transcription server using `faster-whisper` and `FastAPI`.

## Features
- **Async Transcription**: Send a recording URL and get a callback when finished.
- **FastAPI**: High-performance API.
- **Dockerized**: Ready for deployment on Hugging Face Spaces or Render.

## API Endpoints
- `GET /health`: Check server status.
- `POST /transcribe`: Transcription endpoint.
