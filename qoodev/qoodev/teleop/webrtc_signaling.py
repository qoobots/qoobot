"""WebRTC 信令客户端

通过 WebSocket 交换 SDP Offer/Answer 和 ICE Candidate，
建立 P2P WebRTC 连接。
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import aiohttp

from .enums import VideoCodec, AudioCodec

logger = logging.getLogger("qoodev.teleop.webrtc")


@dataclass
class VideoTrackConfig:
    """视频轨道配置"""
    track_id: str = ""
    label: str = "main"          # "main", "depth", "gripper", "rear"
    codec: VideoCodec = VideoCodec.H264
    width: int = 1280
    height: int = 720
    max_fps: int = 30
    max_bitrate_kbps: int = 8000
    keyframe_interval_s: int = 2
    enabled: bool = True


@dataclass
class AudioTrackConfig:
    """音频轨道配置"""
    codec: AudioCodec = AudioCodec.OPUS
    sample_rate: int = 48000
    channels: int = 1            # mono
    max_bitrate_kbps: int = 128
    echo_cancellation: bool = True
    noise_suppression: bool = True
    auto_gain_control: bool = True
    enabled: bool = True


@dataclass
class MediaConfig:
    """媒体流配置"""
    session_id: str = ""
    video_tracks: List[VideoTrackConfig] = field(default_factory=list)
    audio_track: AudioTrackConfig = field(default_factory=AudioTrackConfig)


class WebRTCSignalingClient:
    """WebRTC 信令客户端

    负责通过 WebSocket 信令通道交换 SDP 和 ICE 候选，
    建立 WebRTC P2P 连接。

    Usage:
        signaling = WebRTCSignalingClient("ws://localhost:8208/ws/teleop/sess_123")
        signaling.on_offer = lambda sdp: ...   # 处理 Offer
        signaling.on_answer = lambda sdp: ...  # 处理 Answer
        await signaling.connect()
        await signaling.send_offer(my_sdp)
    """

    def __init__(self, ws_url: str, role: str = "operator"):
        """
        Args:
            ws_url: WebSocket 信令服务器 URL
            role: "operator" 或 "robot"
        """
        self.ws_url = ws_url
        self.role = role
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False

        # SDP 回调
        self.on_offer: Optional[Callable[[str], None]] = None
        self.on_answer: Optional[Callable[[str], None]] = None
        self.on_ice_candidate: Optional[Callable[[str, str, int], None]] = None
        self.on_stream_control: Optional[Callable[[dict], None]] = None
        self.on_media_config: Optional[Callable[[MediaConfig], None]] = None

    async def connect(self) -> None:
        """连接到信令服务器"""
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self.ws_url)
        self._running = True
        asyncio.create_task(self._receive_loop())
        logger.info(f"WebRTC signaling connected: {self.ws_url}")

    async def disconnect(self) -> None:
        """断开信令连接"""
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session:
            await self._session.close()
        logger.info("WebRTC signaling disconnected")

    async def send_offer(self, sdp: str) -> None:
        """发送 SDP Offer"""
        await self._send({
            "type": "webrtc.offer",
            "payload": {"sdp": sdp}
        })

    async def send_answer(self, sdp: str) -> None:
        """发送 SDP Answer"""
        await self._send({
            "type": "webrtc.answer",
            "payload": {"sdp": sdp}
        })

    async def send_ice_candidate(self, candidate: str, sdp_mid: str,
                                   sdp_mline_index: int) -> None:
        """发送 ICE Candidate"""
        await self._send({
            "type": "webrtc.ice_candidate",
            "payload": {
                "candidate": candidate,
                "sdp_mid": sdp_mid,
                "sdp_mline_index": sdp_mline_index
            }
        })

    async def send_media_config(self, config: MediaConfig) -> None:
        """发送媒体配置"""
        await self._send({
            "type": "media.config",
            "payload": {
                "video_tracks": [
                    {
                        "track_id": v.track_id,
                        "label": v.label,
                        "codec": v.codec.value,
                        "resolution": {"width": v.width, "height": v.height},
                        "max_fps": v.max_fps,
                        "max_bitrate_kbps": v.max_bitrate_kbps,
                        "enabled": v.enabled
                    }
                    for v in config.video_tracks
                ],
                "audio_track": {
                    "codec": config.audio_track.codec.value,
                    "sample_rate": config.audio_track.sample_rate,
                    "channels": config.audio_track.channels,
                    "enabled": config.audio_track.enabled
                }
            }
        })

    async def send_stream_control(self, action: str, track_id: str) -> None:
        """发送流控制指令"""
        await self._send({
            "type": "stream.control",
            "payload": {"action": action, "track_id": track_id}
        })

    # ========== 内部方法 ==========

    async def _send(self, message: dict) -> None:
        if self._ws and not self._ws.closed:
            await self._ws.send_json(message)

    async def _receive_loop(self) -> None:
        while self._running:
            try:
                msg = await self._ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED,
                                  aiohttp.WSMsgType.ERROR):
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Signaling receive error: {e}")

    async def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})

        if msg_type == "webrtc.offer" and self.on_offer:
            self.on_offer(payload.get("sdp", ""))

        elif msg_type == "webrtc.answer" and self.on_answer:
            self.on_answer(payload.get("sdp", ""))

        elif msg_type == "webrtc.ice_candidate" and self.on_ice_candidate:
            self.on_ice_candidate(
                payload.get("candidate", ""),
                payload.get("sdp_mid", ""),
                payload.get("sdp_mline_index", 0)
            )

        elif msg_type == "media.config" and self.on_media_config:
            config = MediaConfig()
            config.video_tracks = [
                VideoTrackConfig(
                    track_id=v["track_id"],
                    label=v["label"],
                    codec=VideoCodec(v["codec"]),
                    width=v["resolution"]["width"],
                    height=v["resolution"]["height"],
                    max_fps=v["max_fps"],
                    max_bitrate_kbps=v["max_bitrate_kbps"],
                    enabled=v["enabled"]
                )
                for v in payload.get("video_tracks", [])
            ]
            self.on_media_config(config)

        elif msg_type == "stream.control" and self.on_stream_control:
            self.on_stream_control(payload)
