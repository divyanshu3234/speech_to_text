import os
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import speech_v1p1beta1 as speech
from starlette.concurrency import run_in_threadpool
import subprocess
import tempfile

app = FastAPI(title="Scalable Speech-to-Text API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

speech_client = speech.SpeechClient()

class AudioRequest(BaseModel):
    audio_url: str
    language_code: str = "en-US"


async def download_audio(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(400, "Failed to download audio")
        return r.content


def convert_webm_to_wav(webm_bytes: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".webm") as webm_file, \
         tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:

        webm_file.write(webm_bytes)
        webm_file.flush()

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", webm_file.name,
                "-ar", "16000", "-ac", "1",
                wav_file.name
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return wav_file.read()


def transcribe_audio(wav_bytes: bytes, language_code: str) -> str:
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

    response = operation.result(timeout=300)

    return " ".join(
        result.alternatives[0].transcript
        for result in response.results
    )


@app.post("/speech-to-text")
async def speech_to_text(req: AudioRequest):
    try:
        webm_bytes = await download_audio(req.audio_url)

        wav_bytes = await run_in_threadpool(
            convert_webm_to_wav, webm_bytes
        )

        transcript = await run_in_threadpool(
            transcribe_audio, wav_bytes, req.language_code
        )

        return {"transcript": transcript}

    except Exception:
        raise HTTPException(500, "Transcription failed")
