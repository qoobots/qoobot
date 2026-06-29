package com.qoobot.qoocloud.teleop.config;

import com.qoobot.qoocloud.teleop.signaling.WebRTCSignalingHandler;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 配置
 *
 * 注册 WebRTC 信令处理端点：/ws/teleop/{sessionId}
 */
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final WebRTCSignalingHandler signalingHandler;

    public WebSocketConfig(WebRTCSignalingHandler signalingHandler) {
        this.signalingHandler = signalingHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(signalingHandler, "/ws/teleop/{sessionId}")
                .setAllowedOrigins("*");
    }
}
