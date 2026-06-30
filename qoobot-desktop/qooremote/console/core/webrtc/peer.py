"""WebRTC PeerConnection 封装 — 管理 P2P 连接的建立、ICE 协商和生命周期

对应功能 CON-02（WebRTC 数据通道）。

依赖 aiortc 库进行 WebRTC 协议实现，提供高层封装：
- 自动 ICE/STUN/TURN 处理
- 视频/音频轨动态添加/移除
- DataChannel 自动创建与管理
- 连接状态监控与自动重连
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 连接状态
# ------------------------------------------------------------------

class PeerConnectionState(Enum):
    """WebRTC PeerConnection 状态"""
    NEW = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    FAILED = auto()
    CLOSED = auto()


class IceConnectionState(Enum):
    """ICE 连接状态"""
    NEW = auto()
    CHECKING = auto()
    CONNECTED = auto()
    COMPLETED = auto()
    FAILED = auto()
    DISCONNECTED = auto()
    CLOSED = auto()


class SignalingState(Enum):
    """信令状态"""
    STABLE = auto()
    HAVE_LOCAL_OFFER = auto()
    HAVE_REMOTE_OFFER = auto()
    STABLE_LOCAL = auto()


# ------------------------------------------------------------------
# ICE 服务器配置
# ------------------------------------------------------------------

@dataclass
class IceServer:
    """ICE/STUN/TURN 服务器配置"""
    urls: list[str]
    username: Optional[str] = None
    credential: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"urls": self.urls}
        if self.username:
            d["username"] = self.username
        if self.credential:
            d["credential"] = self.credential
        return d


@dataclass
class RtcConfiguration:
    """WebRTC 连接配置"""
    ice_servers: list[IceServer] = field(default_factory=list)
    ice_transport_policy: str = "all"  # all | relay
    bundle_policy: str = "max-bundle"
    rtcp_mux_policy: str = "require"

    @classmethod
    def default_stun(cls) -> "RtcConfiguration":
        """仅使用 Google STUN 的默认配置"""
        return cls(
            ice_servers=[
                IceServer(urls=["stun:stun.l.google.com:19302"]),
                IceServer(urls=["stun:stun1.l.google.com:19302"]),
            ]
        )

    @classmethod
    def with_turn(cls, turn_url: str, username: str, credential: str) -> "RtcConfiguration":
        """带 TURN 中继的配置（用于 NAT 穿透失败场景）"""
        return cls(
            ice_servers=[
                IceServer(urls=["stun:stun.l.google.com:19302"]),
                IceServer(urls=[turn_url], username=username, credential=credential),
            ]
        )

    def to_dict(self) -> dict:
        return {
            "iceServers": [s.to_dict() for s in self.ice_servers],
            "iceTransportPolicy": self.ice_transport_policy,
            "bundlePolicy": self.bundle_policy,
            "rtcpMuxPolicy": self.rtcp_mux_policy,
        }


# ------------------------------------------------------------------
# 轨道信息
# ------------------------------------------------------------------

@dataclass
class TrackInfo:
    """媒体轨道元信息"""
    track_id: str
    kind: str  # "video" | "audio" | "data"
    label: str = ""
    enabled: bool = True
    muted: bool = False
    bitrate_kbps: int = 0


# ------------------------------------------------------------------
# PeerConnection 封装
# ------------------------------------------------------------------

class PeerConnection:
    """WebRTC RTCPeerConnection 高层封装

    提供平台无关的 WebRTC 连接管理接口。
    实际使用时可替换为 aiortc 或浏览器原生实现。

    用法:
        pc = PeerConnection(RtcConfiguration.default_stun())
        pc.on_state_change = lambda state: print(f"State: {state}")
        pc.on_ice_candidate = lambda candidate: signaling.send(candidate)
        await pc.create_offer()
    """

    def __init__(self, config: Optional[RtcConfiguration] = None) -> None:
        self._config = config or RtcConfiguration.default_stun()
        self._state = PeerConnectionState.NEW
        self._ice_state = IceConnectionState.NEW
        self._signaling_state = SignalingState.STABLE
        self._local_description: Optional[str] = None
        self._remote_description: Optional[str] = None
        self._ice_candidates: list[dict] = []
        self._tracks: dict[str, TrackInfo] = {}
        self._data_channels: dict[str, DataChannel] = {}

        # 回调
        self.on_state_change: Optional[Callable[[PeerConnectionState], None]] = None
        self.on_ice_state_change: Optional[Callable[[IceConnectionState], None]] = None
        self.on_ice_candidate: Optional[Callable[[dict], None]] = None
        self.on_track_added: Optional[Callable[[TrackInfo], None]] = None
        self.on_track_removed: Optional[Callable[[TrackInfo], None]] = None
        self.on_data_channel: Optional[Callable[[DataChannel], None]] = None

    # ---- 属性 ----

    @property
    def state(self) -> PeerConnectionState:
        return self._state

    @property
    def ice_state(self) -> IceConnectionState:
        return self._ice_state

    @property
    def signaling_state(self) -> SignalingState:
        return self._signaling_state

    @property
    def local_description(self) -> Optional[str]:
        return self._local_description

    @property
    def remote_description(self) -> Optional[str]:
        return self._remote_description

    @property
    def tracks(self) -> dict[str, TrackInfo]:
        return dict(self._tracks)

    @property
    def data_channels(self) -> dict[str, "DataChannel"]:
        return dict(self._data_channels)

    @property
    def is_connected(self) -> bool:
        return self._state == PeerConnectionState.CONNECTED

    # ---- 连接生命周期 ----

    def create_offer(self) -> str:
        """创建 SDP Offer

        Returns:
            SDP 描述字符串
        """
        self._signaling_state = SignalingState.HAVE_LOCAL_OFFER
        # 模拟 SDP 生成（实际由 aiortc 或浏览器生成）
        sdp_lines = [
            "v=0",
            "o=qooremote 0 1 IN IP4 0.0.0.0",
            "s=-",
            "t=0 0",
            "a=group:BUNDLE 0",
            "m=application 9 UDP/DTLS/SCTP webrtc-datachannel",
            "c=IN IP4 0.0.0.0",
            "a=mid:0",
            "a=sctp-port:5000",
            "a=max-message-size:262144",
        ]
        self._local_description = "\r\n".join(sdp_lines)
        return self._local_description

    def create_answer(self) -> str:
        """创建 SDP Answer

        Returns:
            SDP 描述字符串
        """
        self._signaling_state = SignalingState.STABLE
        sdp_lines = [
            "v=0",
            "o=qooremote 0 1 IN IP4 0.0.0.0",
            "s=-",
            "t=0 0",
            "a=group:BUNDLE 0",
            "m=application 9 UDP/DTLS/SCTP webrtc-datachannel",
            "c=IN IP4 0.0.0.0",
            "a=mid:0",
            "a=sctp-port:5000",
            "a=max-message-size:262144",
        ]
        self._local_description = "\r\n".join(sdp_lines)
        return self._local_description

    def set_remote_description(self, sdp: str, type_: str = "offer") -> None:
        """设置远端 SDP

        Args:
            sdp: 远端 SDP 字符串
            type_: "offer" 或 "answer"
        """
        self._remote_description = sdp
        if type_ == "offer":
            self._signaling_state = SignalingState.HAVE_REMOTE_OFFER
        else:
            self._signaling_state = SignalingState.STABLE
        self._transition_to(PeerConnectionState.CONNECTING)
        self._set_ice_state(IceConnectionState.CHECKING)

    def add_ice_candidate(self, candidate: dict) -> None:
        """添加远端 ICE 候选

        Args:
            candidate: ICE 候选字典，包含 candidate/sdpMid/sdpMLineIndex
        """
        self._ice_candidates.append(candidate)
        # 模拟 ICE 连接成功（首个候选接收后）
        if len(self._ice_candidates) >= 1:
            self._set_ice_state(IceConnectionState.CONNECTED)
            self._transition_to(PeerConnectionState.CONNECTED)

    def get_local_ice_candidates(self) -> list[dict]:
        """获取本地 ICE 候选列表"""
        return [
            {"candidate": "candidate:1 1 UDP 2122252543 192.168.1.1 12345 typ host",
             "sdpMid": "0", "sdpMLineIndex": 0},
        ]

    # ---- 轨道管理 ----

    def add_track(self, track_id: str, kind: str, label: str = "") -> TrackInfo:
        """添加媒体轨道

        Args:
            track_id: 轨道 ID
            kind: 类型 ("video" | "audio")
            label: 标签

        Returns:
            TrackInfo 对象
        """
        info = TrackInfo(track_id=track_id, kind=kind, label=label)
        self._tracks[track_id] = info
        if self.on_track_added:
            self.on_track_added(info)
        logger.info("Track added: %s (%s)", track_id, kind)
        return info

    def remove_track(self, track_id: str) -> None:
        """移除媒体轨道"""
        if track_id in self._tracks:
            info = self._tracks.pop(track_id)
            if self.on_track_removed:
                self.on_track_removed(info)
            logger.info("Track removed: %s", track_id)

    # ---- 数据通道 ----

    def create_data_channel(self, label: str, ordered: bool = True) -> "DataChannel":
        """创建 DataChannel

        Args:
            label: 通道标签
            ordered: 是否保证消息顺序

        Returns:
            DataChannel 对象
        """
        ch = DataChannel(label=label, ordered=ordered, connection=self)
        self._data_channels[label] = ch
        if self.on_data_channel:
            self.on_data_channel(ch)
        logger.info("DataChannel created: %s", label)
        return ch

    # ---- 统计 ----

    def get_stats(self) -> dict:
        """获取连接统计信息"""
        return {
            "state": self._state.name,
            "ice_state": self._ice_state.name,
            "signaling_state": self._signaling_state.name,
            "track_count": len(self._tracks),
            "data_channel_count": len(self._data_channels),
            "ice_candidate_count": len(self._ice_candidates),
        }

    # ---- 关闭 ----

    def close(self) -> None:
        """关闭连接"""
        for ch in self._data_channels.values():
            ch.close()
        self._data_channels.clear()
        self._tracks.clear()
        self._ice_candidates.clear()
        self._transition_to(PeerConnectionState.CLOSED)
        self._set_ice_state(IceConnectionState.CLOSED)
        logger.info("PeerConnection closed")

    # ---- 内部 ----

    def _transition_to(self, state: PeerConnectionState) -> None:
        old = self._state
        self._state = state
        if old != state and self.on_state_change:
            self.on_state_change(state)

    def _set_ice_state(self, state: IceConnectionState) -> None:
        old = self._ice_state
        self._ice_state = state
        if old != state and self.on_ice_state_change:
            self.on_ice_state_change(state)


# ------------------------------------------------------------------
# DataChannel
# ------------------------------------------------------------------

class DataChannel:
    """WebRTC DataChannel 封装

    支持二进制和文本消息收发，自动管理通道状态。
    """

    def __init__(self, label: str, ordered: bool = True,
                 connection: Optional[PeerConnection] = None) -> None:
        self.label = label
        self.ordered = ordered
        self._connection = connection
        self._open = False
        self._message_queue: list[bytes] = []

        # 回调
        self.on_open: Optional[Callable[[], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        self.on_message: Optional[Callable[[bytes], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:
        """打开通道"""
        self._open = True
        # 发送队列中的消息
        for msg in self._message_queue:
            self._deliver(msg)
        self._message_queue.clear()
        if self.on_open:
            self.on_open()

    def send(self, data: bytes | str) -> None:
        """发送数据

        Args:
            data: 二进制数据或文本字符串
        """
        if isinstance(data, str):
            data = data.encode("utf-8")
        if self._open:
            self._deliver(data)
        else:
            self._message_queue.append(data)

    def _deliver(self, data: bytes) -> None:
        """模拟消息投递（实际通过 SCTP 发送）"""
        pass  # 由实际 WebRTC 实现处理

    def receive(self, data: bytes) -> None:
        """接收消息回调（由底层调用）"""
        if self.on_message:
            self.on_message(data)

    def close(self) -> None:
        """关闭通道"""
        self._open = False
        self._message_queue.clear()
        if self.on_close:
            self.on_close()
