package com.qoobot.qooauth.common.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * Publish audit events to Kafka for async processing by qooauth-audit service.
 * <p>
 * All qooauth services (auth, user, device, security, etc.) use this
 * shared publisher to emit audit events. Events are asynchronously
 * consumed and persisted by the audit service.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuditEventPublisher {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    private static final String TOPIC = "qooauth.audit.events";

    /**
     * Publish an audit event to Kafka.
     *
     * @param actorType    USER / DEVICE / SERVICE / ADMIN / SYSTEM
     * @param actorId      unique identifier of the actor
     * @param actorName    human-readable name (optional)
     * @param action       LOGIN / REGISTER / TOKEN_ISSUE / etc.
     * @param resourceType resource type (optional)
     * @param resourceId   resource identifier (optional)
     * @param resourceName resource name (optional)
     * @param result       SUCCESS / FAILURE / DENIED / ERROR
     * @param errorCode    error code if failed (optional)
     * @param clientIp     client IP (optional)
     * @param userAgent    user agent (optional)
     * @param sessionId    session ID (optional)
     * @param clientId     OAuth2 client ID (optional)
     * @param authMethod   authentication method (optional)
     * @param details      additional details (optional)
     * @param traceId      distributed trace ID (optional)
     */
    public void publish(String actorType, String actorId, String actorName,
                        String action,
                        String resourceType, String resourceId, String resourceName,
                        String result, String errorCode,
                        String clientIp, String userAgent,
                        String sessionId, String clientId, String authMethod,
                        Map<String, Object> details,
                        String traceId) {

        Map<String, Object> event = Map.of(
                "eventId", UUID.randomUUID().toString(),
                "eventTime", Instant.now().toString(),
                "actorType", actorType,
                "actorId", actorId,
                "actorName", actorName != null ? actorName : "",
                "action", action,
                "resourceType", resourceType != null ? resourceType : "",
                "resourceId", resourceId != null ? resourceId : "",
                "resourceName", resourceName != null ? resourceName : "",
                "result", result,
                "errorCode", errorCode != null ? errorCode : "",
                "errorMessage", "",
                "clientIp", clientIp != null ? clientIp : "",
                "userAgent", userAgent != null ? userAgent : "",
                "geoCountry", "",
                "geoCity", "",
                "geoRegion", "",
                "requestId", "",
                "sessionId", sessionId != null ? sessionId : "",
                "clientId", clientId != null ? clientId : "",
                "authMethod", authMethod != null ? authMethod : "",
                "details", details != null ? details : Map.of(),
                "traceId", traceId != null ? traceId : "",
                "spanId", ""
        );

        try {
            String payload = objectMapper.writeValueAsString(event);
            CompletableFuture<SendResult<String, String>> future = kafkaTemplate.send(TOPIC, actorId, payload);
            future.whenComplete((result2, ex) -> {
                if (ex != null) {
                    log.error("Failed to publish audit event: action={}, actor={}, error={}",
                            action, actorId, ex.getMessage());
                }
            });
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize audit event: action={}, actor={}", action, actorId, e);
        }
    }

    /**
     * Convenience method: publish a login audit event.
     */
    public void publishLoginEvent(String userId, String username, String result,
                                   String errorCode, String clientIp, String userAgent,
                                   String sessionId, String authMethod) {
        publish("USER", userId, username,
                "LOGIN", "USER", userId, username,
                result, errorCode,
                clientIp, userAgent,
                sessionId, null, authMethod,
                null, null);
    }

    /**
     * Convenience method: publish a token event.
     */
    public void publishTokenEvent(String action, String userId, String username,
                                   String result, String sessionId, String clientId) {
        publish("USER", userId, username,
                action, "TOKEN", null, null,
                result, null,
                null, null,
                sessionId, clientId, null,
                null, null);
    }

    /**
     * Convenience method: publish an API key event.
     */
    public void publishApiKeyEvent(String action, String userId, String username,
                                    String result, String keyId) {
        publish("USER", userId, username,
                action, "API_KEY", keyId, null,
                result, null,
                null, null,
                null, null, null,
                null, null);
    }
}
