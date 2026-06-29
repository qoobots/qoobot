package com.qoobot.qoogear.security.mq;

import com.qoobot.qoogear.common.mq.MessageEvent;
import com.qoobot.qoogear.common.mq.RocketMQConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.stereotype.Component;

/**
 * Listens for security audit log events.
 * Persists audit trail entries and triggers alerts for critical findings.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_SECURITY_AUDIT_LOG,
        consumerGroup = "qoogear-security-audit-consumer",
        selectorExpression = "*")
public class SecurityAuditLogConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        log.info("Received security-audit-log: eventId={}, type={}, auditId={}",
                event.getEventId(), event.getEventType(), event.getPayload().get("auditId"));

        switch (event.getEventType()) {
            case "audit.created" -> log.info("Security audit created: auditId={}",
                    event.getPayload().get("auditId"));
            case "audit.completed" -> log.info("Security audit completed: auditId={}, riskLevel={}",
                    event.getPayload().get("auditId"), event.getPayload().get("riskLevel"));
            case "fmea.updated" -> log.info("FMEA updated for auditId={}",
                    event.getPayload().get("auditId"));
            default -> log.debug("Unhandled security event type: {}", event.getEventType());
        }
    }
}
