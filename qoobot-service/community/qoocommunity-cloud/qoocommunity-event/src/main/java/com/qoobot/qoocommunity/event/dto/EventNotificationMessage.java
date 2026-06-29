package com.qoobot.qoocommunity.event.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 活动通知消息 DTO，用于通过 RocketMQ 在不同微服务之间传递活动相关通知。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EventNotificationMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 事件唯一标识 */
    private String messageId;

    /** 通知类型：EVENT_PUBLISHED / REGISTRATION_CONFIRMED / EVENT_REMINDER / EVENT_CANCELLED */
    private String notificationType;

    /** 活动 ID */
    private Long eventId;

    /** 活动标题 */
    private String eventTitle;

    /** 活动 slug */
    private String eventSlug;

    /** 活动类型 (DEVCON/HACKATHON/TECHTALK/WEBINAR/MEETUP) */
    private String eventType;

    /** 活动开始时间 */
    private LocalDateTime eventStartTime;

    /** 活动结束时间 */
    private LocalDateTime eventEndTime;

    /** 活动地点 */
    private String eventLocation;

    /** 目标用户 ID（可为空，如广播通知） */
    private String userId;

    /** 通知标题 */
    private String title;

    /** 通知内容 */
    private String content;

    /** 消息产生时间戳 */
    private LocalDateTime timestamp;

    /**
     * 创建活动发布通知消息
     */
    public static EventNotificationMessage eventPublished(Long eventId, String eventTitle,
                                                            String eventSlug, String eventType,
                                                            LocalDateTime startTime, LocalDateTime endTime,
                                                            String location) {
        return EventNotificationMessage.builder()
                .notificationType("EVENT_PUBLISHED")
                .eventId(eventId)
                .eventTitle(eventTitle)
                .eventSlug(eventSlug)
                .eventType(eventType)
                .eventStartTime(startTime)
                .eventEndTime(endTime)
                .eventLocation(location)
                .title("新活动发布")
                .content(String.format("新活动「%s」已发布，欢迎报名参加！", eventTitle))
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 创建报名确认通知消息
     */
    public static EventNotificationMessage registrationConfirmed(Long eventId, String eventTitle,
                                                                   String eventSlug, String eventType,
                                                                   LocalDateTime startTime, LocalDateTime endTime,
                                                                   String location, String userId) {
        return EventNotificationMessage.builder()
                .notificationType("REGISTRATION_CONFIRMED")
                .eventId(eventId)
                .eventTitle(eventTitle)
                .eventSlug(eventSlug)
                .eventType(eventType)
                .eventStartTime(startTime)
                .eventEndTime(endTime)
                .eventLocation(location)
                .userId(userId)
                .title("报名确认")
                .content(String.format("您已成功报名活动「%s」，活动将于 %s 开始", eventTitle, startTime))
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 创建活动提醒通知消息
     */
    public static EventNotificationMessage eventReminder(Long eventId, String eventTitle,
                                                          String eventSlug, String eventType,
                                                          LocalDateTime startTime, LocalDateTime endTime,
                                                          String location, String userId) {
        return EventNotificationMessage.builder()
                .notificationType("EVENT_REMINDER")
                .eventId(eventId)
                .eventTitle(eventTitle)
                .eventSlug(eventSlug)
                .eventType(eventType)
                .eventStartTime(startTime)
                .eventEndTime(endTime)
                .eventLocation(location)
                .userId(userId)
                .title("活动即将开始")
                .content(String.format("您报名的活动「%s」即将于 %s 开始，请准时参加", eventTitle, startTime))
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * 创建活动取消通知消息
     */
    public static EventNotificationMessage eventCancelled(Long eventId, String eventTitle,
                                                           String eventSlug, String eventType,
                                                           LocalDateTime startTime, LocalDateTime endTime,
                                                           String location, String userId) {
        return EventNotificationMessage.builder()
                .notificationType("EVENT_CANCELLED")
                .eventId(eventId)
                .eventTitle(eventTitle)
                .eventSlug(eventSlug)
                .eventType(eventType)
                .eventStartTime(startTime)
                .eventEndTime(endTime)
                .eventLocation(location)
                .userId(userId)
                .title("活动取消通知")
                .content(String.format("很抱歉，您报名的活动「%s」已被取消", eventTitle))
                .timestamp(LocalDateTime.now())
                .build();
    }
}
