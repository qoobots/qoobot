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
 * Listens for certificate-issued events.
 * Triggers downstream processes like auth chip provisioning and notification dispatch.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_CERT_ISSUED,
        consumerGroup = "qoogear-cert-issued-consumer",
        selectorExpression = "*")
public class CertIssuedConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        log.info("Received cert-issued: eventId={}, certNumber={}, developerId={}",
                event.getEventId(),
                event.getPayload().get("certNumber"),
                event.getPayload().get("developerId"));

        // Trigger auth chip burning workflow
        log.info("Initiating auth chip provisioning for certNumber={}", event.getPayload().get("certNumber"));
        // Notification dispatch would be triggered here
    }
}
