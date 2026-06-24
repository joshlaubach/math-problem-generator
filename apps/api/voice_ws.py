"""
Voice WebSocket — proxies browser PCM audio to Deepgram streaming STT.

Endpoint:  ws://host/ws/voice/{session_id}
Auth:      Sec-WebSocket-Protocol bearer token (same as tutor WS)
Encoding:  browser sends Int16 PCM, 16 kHz mono (from AudioWorklet)

Browser → server:
  Binary bytes:  PCM frame chunks (Int16 little-endian, 16 kHz mono)
  JSON {"type": "close"}:  graceful disconnect request

Server → browser:
  {"type": "ready"}
      Deepgram connected — client should start streaming audio
  {"type": "interim", "text": "...", "confidence": 0.85}
      Deepgram interim transcript (word-level)
  {"type": "speech_final", "text": "...", "confidence": 0.95}
      Utterance complete (800ms of silence).  Client should send to tutor.
  {"type": "error", "code": int, "message": "..."}
      Non-fatal error (logged; stream continues if possible)

Close codes:
  4001 — auth failure
  4003 — Deepgram connection failed (key missing or network error)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["voice"])
logger = logging.getLogger(__name__)

# 800 ms of trailing silence in Deepgram triggers speech_final=true.
# Matches the plan decision: "800ms sustained speech before interrupting."
_DEEPGRAM_ENDPOINTING_MS = 800

_DG_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-2"
    "&smart_format=true"
    "&interim_results=true"
    f"&endpointing={_DEEPGRAM_ENDPOINTING_MS}"
    "&encoding=linear16"
    "&sample_rate=16000"
    "&channels=1"
)


async def _authenticate_voice_token(token: Optional[str]):
    """Validate the bearer token. Raises ValueError on failure."""
    from ws_router import _authenticate_ws_token
    return await _authenticate_ws_token(token)


@router.websocket("/ws/voice/{session_id}")
async def voice_ws(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    Proxy browser PCM audio frames to Deepgram streaming STT, then relay
    transcripts back to the browser.  Runs two concurrent tasks:

    1. browser_to_deepgram  — reads binary frames from browser WS, writes to DG
    2. deepgram_to_browser  — reads DG transcript messages, writes JSON to browser WS

    The first task to exit (on disconnect or error) cancels the other.
    """
    # ── Auth (same subprotocol pattern as tutor WS) ───────────────────────────
    subprotocols = websocket.scope.get("subprotocols", []) or []
    token: Optional[str] = None
    accept_subprotocol: Optional[str] = None
    if len(subprotocols) >= 2 and subprotocols[0] == "bearer":
        token = subprotocols[1]
        accept_subprotocol = "bearer"

    await websocket.accept(subprotocol=accept_subprotocol)

    try:
        user = await _authenticate_voice_token(token)
    except ValueError as exc:
        await _send_json(websocket, {"type": "error", "code": 4001, "message": str(exc)})
        await _safe_close(websocket, 4001)
        return

    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not deepgram_key:
        await _send_json(websocket, {
            "type": "error", "code": 4003,
            "message": "Voice unavailable — DEEPGRAM_API_KEY not configured.",
        })
        await _safe_close(websocket, 4003)
        return

    # ── Connect to Deepgram ───────────────────────────────────────────────────
    try:
        import websockets as ws_lib

        dg_conn = await ws_lib.connect(
            _DG_URL,
            extra_headers={"Authorization": f"Token {deepgram_key}"},
            max_size=16 * 1024 * 1024,  # 16 MB — audio frames can burst
            open_timeout=10,
        )
    except Exception as exc:
        logger.error("Deepgram WS connect failed (session=%s): %s", session_id, exc)
        await _send_json(websocket, {
            "type": "error", "code": 4003,
            "message": "Could not connect to transcription service. Try again.",
        })
        await _safe_close(websocket, 4003)
        return

    await _send_json(websocket, {"type": "ready"})
    logger.info("Voice WS opened  session=%s user=%s", session_id, user.id)

    # ── Proxy tasks ───────────────────────────────────────────────────────────

    async def browser_to_deepgram() -> None:
        """Forward binary audio frames from the browser to Deepgram."""
        try:
            while True:
                msg = await websocket.receive()
                mtype = msg.get("type", "")
                if mtype == "websocket.disconnect":
                    break
                if mtype == "websocket.receive":
                    raw_bytes = msg.get("bytes")
                    raw_text = msg.get("text")
                    if raw_bytes:
                        await dg_conn.send(raw_bytes)
                    elif raw_text:
                        try:
                            data = json.loads(raw_text)
                            if data.get("type") == "close":
                                break
                        except Exception:
                            pass
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug("browser_to_deepgram error session=%s: %s", session_id, exc)
        finally:
            # Signal Deepgram that the audio stream has ended
            try:
                await dg_conn.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass

    async def deepgram_to_browser() -> None:
        """Forward Deepgram transcripts back to the browser."""
        try:
            async for raw_msg in dg_conn:
                if isinstance(raw_msg, bytes):
                    continue  # Deepgram rarely sends binary; skip
                try:
                    data = json.loads(raw_msg)
                except Exception:
                    continue

                dg_type = data.get("type", "")

                if dg_type == "Results":
                    channel = data.get("channel", {})
                    alts = channel.get("alternatives", [])
                    if not alts:
                        continue
                    transcript = alts[0].get("transcript", "").strip()
                    confidence = float(alts[0].get("confidence", 0.0))
                    speech_final = data.get("speech_final", False)
                    is_final = data.get("is_final", False)

                    if not transcript:
                        continue

                    if speech_final:
                        await _send_json(websocket, {
                            "type": "speech_final",
                            "text": transcript,
                            "confidence": confidence,
                        })
                    elif is_final or transcript:
                        await _send_json(websocket, {
                            "type": "interim",
                            "text": transcript,
                            "confidence": confidence,
                        })

                elif dg_type == "Error":
                    logger.warning("Deepgram error session=%s: %s", session_id, data)
                elif dg_type == "Metadata":
                    pass  # connection metadata, ignore

        except Exception as exc:
            logger.debug("deepgram_to_browser error session=%s: %s", session_id, exc)

    # ── Run concurrently; first task to exit cancels the other ───────────────
    done, pending = await asyncio.wait(
        [
            asyncio.create_task(browser_to_deepgram(), name="b2dg"),
            asyncio.create_task(deepgram_to_browser(), name="dg2b"),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # ── Cleanup ───────────────────────────────────────────────────────────────
    try:
        await dg_conn.close()
    except Exception:
        pass
    await _safe_close(websocket, 1000)
    logger.info("Voice WS closed  session=%s", session_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send_json(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except Exception:
        pass


async def _safe_close(ws: WebSocket, code: int) -> None:
    try:
        await ws.close(code=code)
    except Exception:
        pass
