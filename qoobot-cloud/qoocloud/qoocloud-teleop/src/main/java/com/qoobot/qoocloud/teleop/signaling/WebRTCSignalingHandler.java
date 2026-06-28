package com.qoobot.qoocloud.teleop.signaling;

import com.qoobot.qoocloud.teleop.service.SessionService;
import com.qoobot.qoocloud.teleop.service.StreamForwarderService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * WebRTC 信令处理 (WebSocket)
 *
 * 处理 SDP 交换、ICE 候选交换、媒体流控制等信令消息。
 * 支持多种消息类型：
 * - sdp: SDP offer/answer 交换
 * - ice: ICE candidate 交换
 * - stream_control: 流暂停/恢复/切换
 * - heartbeat: 心跳保活
 */
@Component
public class WebRTCSignalingHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(WebRTCSignalingHandler.class);

    private final SessionService sessionService;
    private final StreamForwarderService streamService;

    // sessionId → WebSocketSession 映射
    private final Map<String, WebSocketSession> operatorSessions = new ConcurrentHashMap<>();
    private final Map<String, WebSocketSession> robotSessions = new ConcurrentHashMap<>();

    public WebRTCSignalingHandler(SessionService sessionService,
                                   StreamForwarderService streamService) {
        this.sessionService = sessionService;
        this.streamService = streamService;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String sessionId = getSessionId(session);
        String role = getRole(session);
        log.info("WebSocket connected: {} role={}", session.getId(), role);

        if ("operator".equals(role)) {
            operatorSessions.put(sessionId, session);
        } else if ("robot".equals(role)) {
            robotSessions.put(sessionId, session);
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        try {
            String payload = message.getPayload();
            Map<String, Object> msg = parseJson(payload);
            String type = (String) msg.get("type");
            String sessionId = getSessionId(session);

            switch (type) {
                case "sdp" -> handleSDP(sessionId, msg);
                case "ice" -> handleICE(sessionId, msg);
                case "stream_control" -> handleStreamControl(sessionId, msg);
                case "heartbeat" -> handleHeartbeat(sessionId, msg);
                default -> log.warn("Unknown message type: {}", type);
            }
        } catch (Exception e) {
            log.error("Error handling message: {}", e.getMessage(), e);
            try {
                session.sendMessage(new TextMessage(
                    "{\"type\":\"error\",\"message\":\"" + e.getMessage() + "\"}"));
            } catch (IOException ignored) {}
        }
    }

    private void handleSDP(String sessionId, Map<String, Object> msg) {
        String sdpType = (String) msg.get("sdpType"); // "offer" or "answer"
        String sdp = (String) msg.get("sdp");
        String from = (String) msg.get("from"); // "operator" or "robot"

        log.debug("SDP {} from {} for session {}", sdpType, from, sessionId);

        // 更新会话
        if ("offer".equals(sdpType)) {
            sessionService.updateWebRTC(sessionId, sdp, null, null);
        } else {
            sessionService.updateWebRTC(sessionId, null, sdp, null);
        }

        // 转发到另一端
        if ("operator".equals(from)) {
            forwardToRobot(sessionId, msg);
        } else {
            forwardToOperator(sessionId, msg);
        }
    }

    private void handleICE(String sessionId, Map<String, Object> msg) {
        String from = (String) msg.get("from");
        log.debug("ICE candidate from {} for session {}", from, sessionId);

        if ("operator".equals(from)) {
            forwardToRobot(sessionId, msg);
        } else {
            forwardToOperator(sessionId, msg);
        }
    }

    @SuppressWarnings("unchecked")
    private void handleStreamControl(String sessionId, Map<String, Object> msg) {
        String trackId = (String) msg.get("trackId");
        String actionStr = (String) msg.get("action");
        Map<String, Object> params = (Map<String, Object>) msg.getOrDefault("params", Map.of());

        StreamForwarderService.StreamAction action =
            StreamForwarderService.StreamAction.valueOf(actionStr.toUpperCase());
        streamService.controlStream(sessionId, trackId, action, params);

        // 转发控制指令到另一端
        String from = (String) msg.get("from");
        if ("operator".equals(from)) {
            forwardToRobot(sessionId, msg);
        }
    }

    private void handleHeartbeat(String sessionId, Map<String, Object> msg) {
        sessionService.heartbeat(sessionId);
    }

    /**
     * 转发消息到操作员端
     */
    public void forwardToOperator(String sessionId, Object message) {
        WebSocketSession ws = operatorSessions.get(sessionId);
        sendMessage(ws, message);
    }

    /**
     * 转发消息到机器人端
     */
    public void forwardToRobot(String sessionId, Object message) {
        WebSocketSession ws = robotSessions.get(sessionId);
        sendMessage(ws, message);
    }

    /**
     * 广播消息到会话双方
     */
    public void broadcast(String sessionId, Object message) {
        forwardToOperator(sessionId, message);
        forwardToRobot(sessionId, message);
    }

    private void sendMessage(WebSocketSession ws, Object message) {
        if (ws != null && ws.isOpen()) {
            try {
                String text = message instanceof String
                    ? (String) message
                    : new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(message);
                ws.sendMessage(new TextMessage(text));
            } catch (IOException e) {
                log.error("Failed to send message: {}", e.getMessage());
            }
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String sessionId = getSessionId(session);
        log.info("WebSocket closed: {} session={} status={}",
            session.getId(), sessionId, status);

        operatorSessions.remove(sessionId);
        robotSessions.remove(sessionId);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        log.error("WebSocket transport error: {} {}", session.getId(), exception.getMessage());
        String sessionId = getSessionId(session);
        operatorSessions.remove(sessionId);
        robotSessions.remove(sessionId);
    }

    private String getSessionId(WebSocketSession session) {
        String path = session.getUri() != null ? session.getUri().getPath() : "";
        // 从路径提取 sessionId: /ws/teleop/{sessionId}?role=operator
        String[] parts = path.split("/");
        return parts.length >= 4 ? parts[3] : "unknown";
    }

    private String getRole(WebSocketSession session) {
        String query = session.getUri() != null ? session.getUri().getQuery() : "";
        if (query != null && query.contains("role=operator")) return "operator";
        if (query != null && query.contains("role=robot")) return "robot";
        return "unknown";
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper()
                .readValue(json, Map.class);
        } catch (Exception e) {
            throw new RuntimeException("Invalid JSON: " + e.getMessage());
        }
    }
}
