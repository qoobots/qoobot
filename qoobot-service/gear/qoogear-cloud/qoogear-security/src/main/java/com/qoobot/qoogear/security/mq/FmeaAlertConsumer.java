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
 * Listens for FMEA alert events when risk levels change.
 * Triggers notification workflows for high/critical risk assessments.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_FMEA_ALERT,
        consumerGroup = "qoogear-fmea-alert-consumer",
        selectorExpression = "*")
public class FmeaAlertConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        String riskLevel = (String) event.getPayload().get("riskLevel");
        String entityType = (String) event.getPayload().get("entityType");
        Object entityId = event.getPayload().get("entityId");

        log.warn("FMEA Alert: riskLevel={}, entityType={}, entityId={}", riskLevel, entityType, entityId);

        if ("critical".equalsIgnoreCase(riskLevel) || "high".equalsIgnoreCase(riskLevel)) {
            log.warn("CRITICAL/HIGH FMEA risk detected for {} id={} — immediate review required",
                    entityType, entityId);
            // Trigger escalation workflow for critical/high risks
        }
    }
}
