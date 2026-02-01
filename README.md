## Speech-to-Text API

Stateless, cloud-deployable speech-to-text backend built with FastAPI, FFmpeg, and Google Cloud Speech, designed for scalability and async workloads.

### Features
- Async API
- Long audio support
- FFmpeg-based audio normalization
- Cloud-deployable

### Requirements
- Python 3.10+
- ffmpeg
- Google Cloud Speech credentials

### Run locally
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4


### Test
Open /docs for Swagger UI

## API Usage

### POST /speech-to-text

```md
## Notes
- Google Cloud credentials must be provided via environment variables
- Colab is supported for testing only
- Designed as a backend service, not a UI application

**Request**
```json
{
  "audio_url": "https://example.com/audio.webm",
  "language_code": "en-US"
}




