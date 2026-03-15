#!/usr/bin/env python3
import argparse
import json
import logging
import uuid
from pydantic import BaseModel
import websockets
from app.core.exceptions import TTSSpeedRatioTooHighError
from app.services.tts.volcengine.protocols import MsgType, full_client_request, receive_message
from typing import Optional
import re


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VolcengineParams(BaseModel):
    speed_ratio: float
    loudness_ratio: float


def get_cluster(voice: str) -> str:
    if voice.startswith("S_"):
        return "volcano_icl"
    return "volcano_tts"


async def run_volcengine(
    appid=True,
    access_token=True,
    voice_type=True,
    cluster="",
    text=True,
    encoding="wav",
    endpoint="wss://openspeech.bytedance.com/api/v1/tts/ws_binary",
    speed_ratio=1.0,
    loudness_ratio=1.0,
    output_path:str = "output.wav",
    emotion:str = None,
):
    # Determine cluster
    cluster = cluster if cluster else get_cluster(voice_type)

    # Connect to server
    headers = {
        "Authorization": f"Bearer;{access_token}",
    }

    logger.info(f"Connecting to {endpoint} with headers: {headers}")
    websocket = await websockets.connect(
        endpoint, additional_headers=headers, max_size=10 * 1024 * 1024
    )
    logger.info(
        f"Connected to WebSocket server, Logid: {websocket.response.headers['x-tt-logid']}",
    )

    try:
        # Prepare request payload
        request = {
            "app": {
                "appid": appid,
                "token": access_token,
                "cluster": cluster,
            },
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": encoding,
                "speed_ratio": speed_ratio,
                "loudness_ratio": loudness_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "submit",
                "with_timestamp": "1",
                "extra_param": json.dumps(
                    {
                        "disable_markdown_filter": False,
                    }
                ),
            },
        }
        if emotion:
            request["audio"]["emotion"] = emotion
            request["audio"]["enable_emotion"] = True

        # Send request
        await full_client_request(websocket, json.dumps(request).encode())

        # Receive audio data
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)

            if msg.type == MsgType.FrontEndResultServer:
                continue
            elif msg.type == MsgType.AudioOnlyServer:
                audio_data.extend(msg.payload)
                if msg.sequence < 0:  # Last message
                    break
            else:
                raise RuntimeError(f"TTS conversion failed: {msg}")

        # Check if we received any audio data
        if not audio_data:
            raise RuntimeError("No audio data received")

        # Save audio file
        with open(output_path, "wb") as f:
            f.write(audio_data)
        logger.info(f"Audio received: {len(audio_data)}, saved to {output_path}")

    finally:
        await websocket.close()
        logger.info("Connection closed")
