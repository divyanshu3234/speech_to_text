# import os
import httpx
import subprocess
import tempfile
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from google.cloud import speech_v1p1beta1 as speech
from starlette.concurrency import run_in_threadpool


# ---------- CONFIG ----------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit
DOWNLOAD_TIMEOUT = 30
TRANSCRIBE_TIMEOUT = 240  # keep below Cloud Run 300s default


# ---------- APP SETUP ----------

app = FastAPI(title="Scalable Speech-to-Text API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict properly
    allow_methods=["POST"],
    allow_headers=["*"],
)

speech_client = speech.SpeechClient()


# ---------- REQUEST MODEL ----------

class AudioRequest(BaseModel):
    audio_url: HttpUrl
    language_code: str = "en-US"


# ---------- HELPERS ----------

async def download_audio(url: str) -> bytes:
    """
    Download audio safely with size and timeout limits.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Invalid URL scheme")

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
        r = await client.get(url)

        if r.status_code != 200:
            raise HTTPException(400, "Failed to download audio")

        content_length = int(r.headers.get("content-length", 0))
        if content_length > MAX_FILE_SIZE:
            raise HTTPException(400, "Audio file too large")

        if len(r.content) > MAX_FILE_SIZE:
            raise HTTPException(400, "Audio file exceeds size limit")

        return r.content


def convert_webm_to_wav(webm_bytes: bytes) -> bytes:
    """
    Convert WEBM (opus) to WAV (16kHz mono LINEAR16).
    Requires ffmpeg installed in container.
    """
    with tempfile.NamedTemporaryFile(suffix=".webm") as webm_file, \
         tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:

        webm_file.write(webm_bytes)
        webm_file.flush()

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", webm_file.name,
                "-ar", "16000",
                "-ac", "1",
                wav_file.name,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        wav_file.seek(0)
        return wav_file.read()


def transcribe_audio(wav_bytes: bytes, language_code: str) -> str:
    """
    Send audio to Google Speech-to-Text.
    """
    audio = speech.RecognitionAudio(content=wav_bytes)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )

    operation = speech_client.long_running_recognize(
        config=config,
        audio=audio,
    )

    response = operation.result(timeout=TRANSCRIBE_TIMEOUT)

    transcripts = [
        result.alternatives[0].transcript
        for result in response.results
    ]

    return " ".join(transcripts)


# ---------- ENDPOINT ----------

@app.post("/speech-to-text")
async def speech_to_text(req: AudioRequest):
    try:
        webm_bytes = await download_audio(str(req.audio_url))

        wav_bytes = await run_in_threadpool(
            convert_webm_to_wav,
            webm_bytes,
        )

        transcript = await run_in_threadpool(
            transcribe_audio,
            wav_bytes,
            req.language_code,
        )

        return {
            "success": True,
            "language": req.language_code,
            "transcript": transcript,
        }

    except HTTPException:
        raise
    except Exception as e:
        
        raise HTTPException(500, f"Transcription failed: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok"}
