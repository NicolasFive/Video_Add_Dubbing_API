#!/usr/bin/env python3
import json
import logging
import uuid
import websockets
from typing import Optional
import re
from app.services.tts.volcengine.protocols_v2 import EventType, MsgType, full_client_request, receive_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




async def run_volcengine(
    appid: str,
    access_token: str,
    text: str,
    resource_id: str = "seed-tts-2.0",
    voice_type: str = "",
    encoding: str = "wav",
    endpoint: str = "wss://openspeech.bytedance.com/api/v3/tts/unidirectional/stream",
    speed_ratio=1.0,
    loudness_ratio=1.0,
    output_path:str = "output.wav",
    emotion:str = None,
    context_texts: Optional[list] = None,
    section_id: Optional[str] = None,
):
    # Connect to server
    headers = {
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Connect-Id": str(uuid.uuid4()),
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
        additions = {
            "disable_markdown_filter": False,
        }
        if context_texts:
            additions["context_texts"] = context_texts
        if section_id:
            additions["section_id"] = section_id
        request = {
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "req_params": {
                "speaker": voice_type,
                "audio_params": {
                    "format": encoding,
                    "sample_rate": 24000,
                    "enable_timestamp": True,
                    "speech_rate": 0.0,  # 语速，取值范围[-50,100]，100代表2.0倍速，-50代表0.5倍数
                    "loudness_rate": 0.0,  # 音量，取值范围[-50,100]，100代表2.0倍音量，-50代表0.5倍音量
                },
                "text": text,
                "additions": json.dumps(additions, ensure_ascii=False),
            },
        }
        speech_rate = round(speed_ratio * 100 - 100)
        loudness_rate = round(loudness_ratio * 100 - 100)
        request["req_params"]["audio_params"]["speech_rate"] = speech_rate
        request["req_params"]["audio_params"]["loudness_rate"] = loudness_rate
        if emotion:
            request["req_params"]["audio_params"]["emotion"] = emotion

        # Send request
        await full_client_request(websocket, json.dumps(request).encode())

        # Receive audio data
        audio_data = bytearray()
        while True:
            msg = await receive_message(websocket)

            if msg.type == MsgType.FullServerResponse:
                if msg.event == EventType.SessionFinished:
                    break
            elif msg.type == MsgType.AudioOnlyServer:
                audio_data.extend(msg.payload)
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
