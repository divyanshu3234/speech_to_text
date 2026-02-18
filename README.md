##  Scalable Speech-to-Text API

A production-ready, containerized Speech-to-Text microservice built with FastAPI, Google Cloud Speech-to-Text, and deployed on Cloud Run.

This service:

Downloads audio from a public URL

Converts WEBM → WAV using ffmpeg

Transcribes speech using Google Cloud Speech API

Returns clean JSON transcript

Built for scalability, async performance, and cloud-native deploym

### Architecture
```json

Client
   ↓
Cloud Run (FastAPI container)
   ↓
Async audio download
   ↓
ffmpeg conversion (WEBM → 16kHz WAV)
   ↓
Google Speech-to-Text (long_running_recognize)
   ↓
JSON transcript response

#
```

**Request via curl**
```json
curl -X POST "https://speech-to-text-api-322039733047.asia-south1.run.app/speech-to-text" \
  -H "Content-Type: application/json" \
  -d '{"audio_url":"https://your-audio-file.webm"}'




