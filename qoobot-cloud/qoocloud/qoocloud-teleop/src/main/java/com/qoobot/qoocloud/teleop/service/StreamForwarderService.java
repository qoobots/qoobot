package com.qoobot.qoocloud.teleop.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * WebRTC 媒体流转发服务 (SFU - Selective Forwarding Unit)
 *
 * 负责视频流、音频流在操作员端与机器人端之间的转发管理。
 * 支持多路视频同时转发，动态码率调整，流暂停/恢复。
 *
 * 注：生产环境建议使用 mediasoup/Janus 等专业 SFU，
 * 此处为逻辑层封装，与底层 SFU 引擎交互。
 */
@Service
public class StreamForwarderService {

    private static final Logger log = LoggerFactory.getLogger(StreamForwarderService.class);

    private final SessionService sessionService;

    // 每个会话的活跃流
    private final Map<String, SessionStreams> sessionStreams = new ConcurrentHashMap<>();

    // 流统计
    private final Map<String, Map<String, StreamStats>> streamStats = new ConcurrentHashMap<>();

    // 默认配置
    private static final int MAX_VIDEO_TRACKS = 4;
    private static final int MAX_AUDIO_TRACKS = 2;
    private static final int DEFAULT_VIDEO_BITRATE_KBPS = 4000;
    private static final int DEFAULT_AUDIO_BITRATE_KBPS = 64;

    public StreamForwarderService(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    /**
     * 注册媒体流
     */
    public StreamInfo registerStream(String sessionId, String trackId,
                                      StreamType type, StreamDirection direction,
                                      Map<String, Object> config) {
        SessionStreams streams = sessionStreams.computeIfAbsent(sessionId,
            k -> new SessionStreams());

        StreamInfo info = new StreamInfo();
        info.trackId = trackId;
        info.type = type;
        info.direction = direction;
        info.codec = (String) config.getOrDefault("codec", type == StreamType.VIDEO ? "h264" : "opus");
        info.width = toInt(config.get("width"), 1280);
        info.height = toInt(config.get("height"), 720);
        info.maxFps = toInt(config.get("maxFps"), 30);
        info.maxBitrateKbps = toInt(config.get("maxBitrateKbps"),
            type == StreamType.VIDEO ? DEFAULT_VIDEO_BITRATE_KBPS : DEFAULT_AUDIO_BITRATE_KBPS);
        info.enabled = true;

        if (type == StreamType.VIDEO) {
            if (streams.videoTracks.size() >= MAX_VIDEO_TRACKS) {
                throw new IllegalStateException(
                    "Max video tracks (" + MAX_VIDEO_TRACKS + ") reached for session: " + sessionId);
            }
            streams.videoTracks.put(trackId, info);
        } else {
            if (streams.audioTracks.size() >= MAX_AUDIO_TRACKS) {
                throw new IllegalStateException(
                    "Max audio tracks (" + MAX_AUDIO_TRACKS + ") reached for session: " + sessionId);
            }
            streams.audioTracks.put(trackId, info);
        }

        log.info("Stream registered: {} track={} type={} dir={} codec={}",
            sessionId, trackId, type, direction, info.codec);
        return info;
    }

    /**
     * 移除媒体流
     */
    public void unregisterStream(String sessionId, String trackId) {
        SessionStreams streams = sessionStreams.get(sessionId);
        if (streams != null) {
            streams.videoTracks.remove(trackId);
            streams.audioTracks.remove(trackId);
        }
        Map<String, StreamStats> stats = streamStats.get(sessionId);
        if (stats != null) {
            stats.remove(trackId);
        }
        log.info("Stream unregistered: {} track={}", sessionId, trackId);
    }

    /**
     * 更新流控制（暂停/恢复/切换分辨率）
     */
    public StreamInfo controlStream(String sessionId, String trackId,
                                     StreamAction action, Map<String, Object> params) {
        SessionStreams streams = sessionStreams.get(sessionId);
        if (streams == null) {
            throw new NoSuchElementException("No streams for session: " + sessionId);
        }

        StreamInfo info = streams.videoTracks.get(trackId);
        if (info == null) {
            info = streams.audioTracks.get(trackId);
        }
        if (info == null) {
            throw new NoSuchElementException("Track not found: " + trackId);
        }

        switch (action) {
            case PAUSE -> info.enabled = false;
            case RESUME -> info.enabled = true;
            case MUTE -> info.muted = true;
            case UNMUTE -> info.muted = false;
            case CHANGE_RESOLUTION -> {
                info.width = toInt(params.get("width"), info.width);
                info.height = toInt(params.get("height"), info.height);
            }
            case CHANGE_BITRATE -> {
                info.maxBitrateKbps = toInt(params.get("maxBitrateKbps"), info.maxBitrateKbps);
            }
        }

        log.info("Stream controlled: {} track={} action={}", sessionId, trackId, action);
        return info;
    }

    /**
     * 更新流统计
     */
    public void updateStreamStats(String sessionId, String trackId,
                                   StreamDirection direction, long bytes,
                                   int bitrateKbps, int fps, int rttMs, int jitterMs,
                                   long packetsSent, long packetsLost) {
        Map<String, StreamStats> stats = streamStats.computeIfAbsent(sessionId,
            k -> new ConcurrentHashMap<>());

        StreamStats s = stats.computeIfAbsent(trackId, k -> new StreamStats());
        s.trackId = trackId;
        s.direction = direction;
        s.bytesSent += bytes;
        s.packetsSent += packetsSent;
        s.packetsLost += packetsLost;
        s.packetLossRate = packetsSent > 0 ? (double) packetsLost / packetsSent : 0;
        s.currentBitrateKbps = bitrateKbps;
        s.currentFps = fps;
        s.rttMs = rttMs;
        s.jitterMs = jitterMs;

        // 同步流量统计到会话
        if (direction == StreamDirection.UPSTREAM) {
            sessionService.updateBytesSent(sessionId,
                bytes, 0); // 简化：实际应区分 video/audio
        }
    }

    /**
     * 获取会话所有流统计
     */
    public AllStreamStats getAllStreamStats(String sessionId) {
        Map<String, StreamStats> stats = streamStats.get(sessionId);
        AllStreamStats result = new AllStreamStats();
        result.sessionId = sessionId;
        result.streams = stats != null ? new ArrayList<>(stats.values()) : List.of();
        result.totalBytesSent = result.streams.stream()
            .mapToLong(s -> s.bytesSent).sum();
        result.totalBytesReceived = result.streams.stream()
            .mapToLong(s -> s.bytesSent).sum(); // SFU 模式下收发量相同
        return result;
    }

    /**
     * 清理会话所有流
     */
    public void cleanupSession(String sessionId) {
        sessionStreams.remove(sessionId);
        streamStats.remove(sessionId);
        log.info("Streams cleaned up for session: {}", sessionId);
    }

    // ========== 内部类型 ==========

    private int toInt(Object value, int defaultValue) {
        if (value instanceof Number n) return n.intValue();
        return defaultValue;
    }

    // ========== 数据类 ==========

    public enum StreamType { VIDEO, AUDIO }
    public enum StreamDirection { UPSTREAM, DOWNSTREAM }
    public enum StreamAction {
        PAUSE, RESUME, MUTE, UNMUTE, CHANGE_RESOLUTION, CHANGE_BITRATE
    }

    public static class StreamInfo {
        public String trackId;
        public StreamType type;
        public StreamDirection direction;
        public String codec;
        public int width;
        public int height;
        public int maxFps;
        public int maxBitrateKbps;
        public boolean enabled;
        public boolean muted;
    }

    public static class StreamStats {
        public String trackId;
        public StreamDirection direction;
        public long bytesSent;
        public long packetsSent;
        public long packetsLost;
        public double packetLossRate;
        public int currentBitrateKbps;
        public int currentFps;
        public int rttMs;
        public int jitterMs;
        public String codec;
    }

    public static class AllStreamStats {
        public String sessionId;
        public List<StreamStats> streams = List.of();
        public long totalBytesSent;
        public long totalBytesReceived;
    }

    private static class SessionStreams {
        final Map<String, StreamInfo> videoTracks = new LinkedHashMap<>();
        final Map<String, StreamInfo> audioTracks = new LinkedHashMap<>();
    }
}
