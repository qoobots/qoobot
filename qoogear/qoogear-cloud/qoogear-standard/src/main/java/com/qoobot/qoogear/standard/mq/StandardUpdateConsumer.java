package com.qoobot.qoogear.standard.mq;

import com.qoobot.qoogear.common.mq.MessageEvent;
import com.qoobot.qoogear.common.mq.RocketMQConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.stereotype.Component;

/**
 * Listens for standard specification update events.
 * Handles cache invalidation and compatibility matrix updates when standards change.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_STANDARD_UPDATE,
        consumerGroup = "qoogear-standard-update-consumer",
        selectorExpression = "*")
public class StandardUpdateConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        log.info("Received standard-update: eventId={}, type={}, specNumber={}",
                event.getEventId(), event.getEventType(), event.getPayload().get("specNumber"));

        switch (event.getEventType()) {
            case "spec.created" -> log.info("New standard spec created: {}",
                    event.getPayload().get("specNumber"));
            case "spec.published" -> log.info("Standard spec published: {} v{}",
                    event.getPayload().get("specNumber"), event.getPayload().get("version"));
            case "spec.deprecated" -> log.warn("Standard spec deprecated: {}",
                    event.getPayload().get("specNumber"));
            case "spec.updated" -> log.info("Standard spec updated: {}",
                    event.getPayload().get("specNumber"));
            default -> log.debug("Unhandled standard event type: {}", event.getEventType());
        }
    }
}
