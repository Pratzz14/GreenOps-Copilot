"""Speech provider failover, input limits, and verified Realtime audio."""

import base64
import json
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import dashboard_chat, dashboard_voice as voice

CLIP = voice.wav_bytes(b"\x01\x00" * voice.INPUT_RATE, voice.INPUT_RATE)
ANSWER = "The total was 42 kWh."
PCM = b"\x02\x00" * 32
ROOT = "/api/v1/dashboard/chat"


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(dashboard_chat, "configured", lambda: True)
    monkeypatch.setattr(voice, "voice_settings", lambda: ("eleven-key", "openai-key", "test-voice"))
    app = FastAPI()
    app.include_router(dashboard_chat.router)
    return TestClient(app)


def mock_http(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(voice.httpx, "AsyncClient",
                        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


def mock_realtime(monkeypatch, text, *, status="completed", extra_audio=False):
    requests = []
    content = {"item_id": "item", "content_index": 0}
    audio = {"type": "response.output_audio.delta", "delta": base64.b64encode(PCM).decode(), **content}
    events = [
        audio,
        {"type": "response.output_audio_transcript.done", "transcript": text, **content},
        {"type": "response.done", "response": {"status": status}},
    ]
    if extra_audio:
        events.insert(1, {**audio, "item_id": "unexpected-audio"})

    class Socket:
        async def send(self, message):
            requests.append(json.loads(message))

        async def __aiter__(self):
            for event in events:
                yield json.dumps(event)

    @asynccontextmanager
    async def connect(url, **kwargs):
        assert url.endswith("model=gpt-realtime-2.1-mini")
        assert kwargs["additional_headers"]["Authorization"] == "Bearer openai-key"
        yield Socket()

    monkeypatch.setattr(voice, "connect", connect)
    return requests


@pytest.mark.parametrize("failure", [None, 401, 429, 503, "timeout", "missing key"])
def test_transcription_falls_back_with_identical_clip(api, monkeypatch, failure):
    visits = []
    if failure == "missing key":
        monkeypatch.setattr(voice, "voice_settings", lambda: ("", "openai-key", "test-voice"))

    def handle(request):
        visits.append(request.url.host)
        assert CLIP in request.content
        if request.url.host == "api.elevenlabs.io":
            assert request.headers["xi-api-key"] == "eleven-key"
            assert b"scribe_v3" in request.content
            if failure == "timeout":
                raise httpx.ReadTimeout("provider timed out", request=request)
            if failure:
                return httpx.Response(failure)
        else:
            assert request.headers["authorization"] == "Bearer openai-key"
            assert b"gpt-transcribe" in request.content
        return httpx.Response(200, json={"text": "Which tool cost the most?"})

    mock_http(monkeypatch, handle)
    response = api.post(ROOT + "/transcribe", headers={"Content-Type": "audio/wav"}, content=CLIP)
    expected = [] if failure == "missing key" else ["api.elevenlabs.io"]
    if failure:
        expected.append("api.openai.com")
    assert visits == expected
    assert response.status_code == 200
    assert response.json() == {"text": "Which tool cost the most?"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("failure", [None, 402, 429])
def test_speech_falls_back_without_changing_answer(api, monkeypatch, failure):
    realtime = mock_realtime(monkeypatch, ANSWER)
    requests = []

    def handle(request):
        requests.append(request)
        assert request.url.path == "/v1/text-to-speech/test-voice"
        assert json.loads(request.content) == {"model_id": "eleven_flash_v2_5", "text": ANSWER}
        if failure:
            return httpx.Response(failure)
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"test audio")

    mock_http(monkeypatch, handle)
    response = api.post(ROOT + "/speech", json={"text": ANSWER})
    assert len(requests) == 1
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    if failure:
        sent = realtime[0]["response"]
        assert sent["input"][0]["content"][0]["text"] == ANSWER
        assert sent["conversation"] == "none"
        assert response.headers["content-type"] == "audio/wav"
        assert response.content == voice.wav_bytes(PCM, voice.OUTPUT_RATE)
    else:
        assert realtime == []
        assert response.headers["content-type"] == "audio/mpeg"


@pytest.mark.parametrize(("transcript", "status", "extra_audio"), [
    ("The total was 24 kWh.", "completed", False),
    ("The total was 42 MWh.", "completed", False),
    ("The total was 42 kwh.", "completed", False),
    ("The total was 42 kWh. Here is more.", "completed", False),
    (ANSWER, "incomplete", False),
    (ANSWER, "completed", True),
])
def test_unverified_narration_is_never_returned(api, monkeypatch, transcript, status, extra_audio):
    mock_http(monkeypatch, lambda request: httpx.Response(503))
    mock_realtime(monkeypatch, transcript, status=status, extra_audio=extra_audio)
    response = api.post(ROOT + "/speech", json={"text": ANSWER})
    assert response.status_code == 502
    assert response.json()["detail"] == "We couldn’t play this answer."


def test_status_and_input_limits(api, monkeypatch):
    calls = []
    mock_http(monkeypatch, lambda request: calls.append(request))
    assert api.get(ROOT + "/status").json() == {"configured": True, "voice_configured": True}
    assert api.post(ROOT + "/transcribe", content=CLIP).status_code == 415
    headers = {"Content-Type": "audio/wav"}
    assert api.post(ROOT + "/transcribe", content=b"bad", headers=headers).status_code == 422
    assert api.post(ROOT + "/transcribe", content=CLIP[:-2], headers=headers).status_code == 422
    too_long = voice.wav_bytes(b"\x00\x00" * (voice.INPUT_RATE * voice.MAX_CLIP_SECONDS + 1), voice.INPUT_RATE)
    assert api.post(ROOT + "/transcribe", content=too_long, headers=headers).status_code == 413
    assert api.post(ROOT + "/transcribe", content=b" " * (voice.MAX_CLIP_BYTES + 1), headers=headers).status_code == 413
    assert api.post(ROOT + "/speech", json={"text": " "}).status_code == 422
    assert api.post(ROOT + "/speech", json={"text": "x" * 2401}).status_code == 422
    assert not calls
    monkeypatch.setattr(voice, "voice_settings", lambda: ("", "", "test-voice"))
    assert api.get(ROOT + "/status").json()["voice_configured"] is False
    assert api.post(ROOT + "/transcribe", content=CLIP, headers=headers).status_code == 503
