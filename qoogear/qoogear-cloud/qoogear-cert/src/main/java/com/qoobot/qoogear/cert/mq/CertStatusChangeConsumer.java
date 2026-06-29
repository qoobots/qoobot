package com.qoobot.qoogear.cert.mq;

import com.qoobot.qoogear.common.mq.MessageEvent;
import com.qoobot.qoogear.common.mq.RocketMQConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.stereotype.Component;

/**
 * Listens for certificate status change events from the message queue.
 * Handles cross-service notifications when certification state changes.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_CERT_STATUS_CHANGE,
        consumerGroup = "qoogear-cert-status-consumer",
        selectorExpression = "*")
public class CertStatusChangeConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        log.info("Received cert-status-change: eventId={}, type={}, source={}, payload={}",
                event.getEventId(), event.getEventType(), event.getSource(), event.getPayload());

        switch (event.getEventType()) {
            case "application.submitted" -> log.info("Processing submission event for appId={}",
                    event.getPayload().get("applicationId"));
            case "application.approved" -> log.info("Processing approval event for appId={}",
                    event.getPayload().get("applicationId"));
            case "application.rejected" -> log.info("Processing rejection event for appId={}",
                    event.getPayload().get("applicationId"));
            case "certificate.issued" -> log.info("Processing certificate issued event for certNumber={}",
                    event.getPayload().get("certNumber"));
            case "certificate.revoked" -> log.warn("Processing certificate revoked event for certNumber={}",
                    event.getPayload().get("certNumber"));
            default -> log.debug("Unhandled event type: {}", event.getEventType());
        }
    }
}
