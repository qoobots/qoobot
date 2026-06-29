package com.qoobot.qoogear.common.mq;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.Map;

/**
 * Generic message event envelope for RocketMQ.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageEvent {
    private String eventId;
    private String eventType;
    private String source;
    private Instant timestamp;
    private Map<String, Object> payload;
}
