package com.qoobot.qoogear.lab.mq;

import com.qoobot.qoogear.common.mq.MessageEvent;
import com.qoobot.qoogear.common.mq.RocketMQConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.stereotype.Component;

/**
 * Listens for lab assignment creation events.
 * Notifies lab technicians and triggers equipment reservation workflows.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
@RocketMQMessageListener(
        topic = RocketMQConfig.TOPIC_LAB_ASSIGNMENT_CREATED,
        consumerGroup = "qoogear-lab-assignment-consumer",
        selectorExpression = "*")
public class LabAssignmentConsumer implements RocketMQListener<MessageEvent> {

    @Override
    public void onMessage(MessageEvent event) {
        log.info("Received lab-assignment-created: eventId={}, appId={}, labId={}",
                event.getEventId(),
                event.getPayload().get("applicationId"),
                event.getPayload().get("labId"));

        // Trigger notification to lab contact
        log.info("Notifying labId={} about new test assignment for appId={}",
                event.getPayload().get("labId"),
                event.getPayload().get("applicationId"));
    }
}
