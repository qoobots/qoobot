package com.qoobot.qoocommunity.event.service;

import com.qoobot.qoocommunity.event.domain.Event;
import com.qoobot.qoocommunity.event.domain.Registration;
import com.qoobot.qoocommunity.event.dto.EventNotificationMessage;
import com.qoobot.qoocommunity.event.repository.RegistrationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

/**
 * 活动通知服务。
 * 负责通过 RocketMQ 发送活动相关异步通知消息。
 *
 * <h3>RocketMQ Topic 约定</h3>
 * <ul>
 *   <li>{@code community.notification} — 通用通知（活动发布、报名确认、活动取消）</li>
 *   <li>{@code community.event.reminder} — 活动开始提醒</li>
 * </ul>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EventNotificationService {

    private final RocketMQTemplate rocketMQTemplate;
    private final RegistrationRepository registrationRepository;

    private static final String TOPIC_NOTIFICATION = "community.notification";
    private static final String TOPIC_EVENT_REMINDER = "community.event.reminder";

    /**
     * 发送活动发布通知（广播给所有潜在参与者）。
     * 消息发送到 {@code community.notification} topic。
     */
    public void notifyEventPublished(Event event) {
        EventNotificationMessage msg = EventNotificationMessage.eventPublished(
                event.getId(), event.getTitle(), event.getSlug(), event.getType(),
                event.getStartTime(), event.getEndTime(), event.getLocation());
        msg.setMessageId(UUID.randomUUID().toString());

        log.info("Sending event published notification: eventId={}, title={}", event.getId(), event.getTitle());
        rocketMQTemplate.convertAndSend(TOPIC_NOTIFICATION, msg);
        log.info("Event published notification sent successfully: eventId={}", event.getId());
    }

    /**
     * 发送报名确认通知给单个用户。
     * 消息发送到 {@code community.notification} topic。
     */
    public void notifyRegistrationConfirmed(Event event, Registration registration) {
        EventNotificationMessage msg = EventNotificationMessage.registrationConfirmed(
                event.getId(), event.getTitle(), event.getSlug(), event.getType(),
                event.getStartTime(), event.getEndTime(), event.getLocation(),
                registration.getUserId());
        msg.setMessageId(UUID.randomUUID().toString());

        log.info("Sending registration confirmed notification: eventId={}, userId={}",
                event.getId(), registration.getUserId());
        rocketMQTemplate.convertAndSend(TOPIC_NOTIFICATION, msg);
        log.info("Registration confirmed notification sent: eventId={}, userId={}",
                event.getId(), registration.getUserId());
    }

    /**
     * 发送活动开始提醒给所有已报名用户。
     * 消息发送到 {@code community.event.reminder} topic。
     * <p>
     * 此方法会查询所有已报名该活动的用户，并为每个用户发送一条提醒消息。
     * 应由定时任务调度，在活动开始前 24 小时和 1 小时各执行一次。
     */
    public void sendEventReminder(Event event) {
        List<Registration> registrations = registrationRepository.findByEventId(event.getId());
        if (registrations.isEmpty()) {
            log.info("No registrations for event {}, skipping reminder", event.getId());
            return;
        }

        log.info("Sending event reminders for event {} to {} attendees",
                event.getId(), registrations.size());

        for (Registration reg : registrations) {
            EventNotificationMessage msg = EventNotificationMessage.eventReminder(
                    event.getId(), event.getTitle(), event.getSlug(), event.getType(),
                    event.getStartTime(), event.getEndTime(), event.getLocation(),
                    reg.getUserId());
            msg.setMessageId(UUID.randomUUID().toString());

            rocketMQTemplate.convertAndSend(TOPIC_EVENT_REMINDER, msg);
            log.debug("Event reminder sent: eventId={}, userId={}", event.getId(), reg.getUserId());
        }

        log.info("Event reminders sent successfully: eventId={}, count={}",
                event.getId(), registrations.size());
    }

    /**
     * 发送活动取消通知给所有已报名用户。
     * 消息发送到 {@code community.notification} topic。
     * <p>
     * 此方法会查询所有已报名该活动的用户，并为每个用户发送一条取消通知。
     */
    public void notifyEventCancelled(Event event) {
        List<Registration> registrations = registrationRepository.findByEventId(event.getId());
        if (registrations.isEmpty()) {
            log.info("No registrations for event {}, skipping cancellation notification", event.getId());
            return;
        }

        log.info("Sending event cancellation notifications for event {} to {} attendees",
                event.getId(), registrations.size());

        for (Registration reg : registrations) {
            EventNotificationMessage msg = EventNotificationMessage.eventCancelled(
                    event.getId(), event.getTitle(), event.getSlug(), event.getType(),
                    event.getStartTime(), event.getEndTime(), event.getLocation(),
                    reg.getUserId());
            msg.setMessageId(UUID.randomUUID().toString());

            rocketMQTemplate.convertAndSend(TOPIC_NOTIFICATION, msg);
            log.debug("Cancellation notification sent: eventId={}, userId={}", event.getId(), reg.getUserId());
        }

        log.info("Event cancellation notifications sent: eventId={}, count={}",
                event.getId(), registrations.size());
    }
}
