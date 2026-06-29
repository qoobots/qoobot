package com.qoobot.qoostore.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 通知服务
 * 邮件通知、站内信、推送通知
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationService {

    private final JavaMailSender mailSender;
    private final ConcurrentHashMap<UUID, List<Notification>> userNotifications = new ConcurrentHashMap<>();

    /**
     * 通知记录
     */
    public record Notification(
            String id,
            UUID userId,
            String type,
            String title,
            String content,
            boolean read,
            LocalDateTime createdAt
    ) {}

    /**
     * 发送邮件通知
     */
    @Async
    public void sendEmail(String to, String subject, String content) {
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setTo(to);
            message.setSubject("[QooStore] " + subject);
            message.setText(content);
            mailSender.send(message);
            log.info("Email sent: to={}, subject={}", to, subject);
        } catch (Exception e) {
            log.error("Failed to send email: to={}, subject={}, error={}", to, subject, e.getMessage());
        }
    }

    /**
     * 发送站内信
     */
    public void sendInAppNotification(UUID userId, String type, String title, String content) {
        Notification notification = new Notification(
                UUID.randomUUID().toString(),
                userId, type, title, content,
                false, LocalDateTime.now()
        );
        userNotifications.computeIfAbsent(userId, k -> new ArrayList<>()).add(0, notification);
        log.info("In-app notification sent: userId={}, type={}, title={}", userId, type, title);
    }

    /**
     * 获取用户站内信
     */
    public List<Notification> getUserNotifications(UUID userId, int page, int size) {
        List<Notification> notifications = userNotifications.getOrDefault(userId, List.of());
        int fromIndex = Math.min(page * size, notifications.size());
        int toIndex = Math.min(fromIndex + size, notifications.size());
        return notifications.subList(fromIndex, toIndex);
    }

    /**
     * 获取未读通知数
     */
    public long getUnreadCount(UUID userId) {
        return userNotifications.getOrDefault(userId, List.of()).stream()
                .filter(n -> !n.read())
                .count();
    }

    /**
     * 标记通知为已读
     */
    public void markAsRead(UUID userId, String notificationId) {
        userNotifications.getOrDefault(userId, List.of()).stream()
                .filter(n -> n.id().equals(notificationId))
                .findFirst()
                .ifPresent(n -> {
                    // Create updated notification and replace
                    userNotifications.get(userId).remove(n);
                    userNotifications.get(userId).add(new Notification(
                            n.id(), n.userId(), n.type(), n.title(), n.content(),
                            true, n.createdAt()
                    ));
                });
    }

    /**
     * 通知开发者：技能审核结果
     */
    public void notifyReviewResult(Long developerId, String skillName, boolean approved, String reason) {
        String title = approved ? "技能审核通过" : "技能审核驳回";
        String content = approved
                ? String.format("您的技能「%s」已通过审核，现已上架商店。", skillName)
                : String.format("您的技能「%s」审核未通过。原因：%s", skillName, reason != null ? reason : "未提供");

        log.info("Review result notification: developerId={}, skillName={}, approved={}", developerId, skillName, approved);
        // In production: lookup developer email and send
    }

    /**
     * 通知用户：技能更新可用
     */
    public void notifySkillUpdate(UUID userId, String skillName, String newVersion, String changelog) {
        String title = "技能更新可用";
        String content = String.format("您安装的技能「%s」有新版本 %s 可用。\n更新内容：%s",
                skillName, newVersion, changelog != null ? changelog : "无");
        sendInAppNotification(userId, "skill_update", title, content);
    }

    /**
     * 通知开发者：收益结算
     */
    public void notifyPayoutProcessed(Long developerId, String amount, String currency, String payoutMethod) {
        String title = "收益结算完成";
        String content = String.format("您的月度收益 %s %s 已通过 %s 完成结算。",
                amount, currency, payoutMethod);
        log.info("Payout notification: developerId={}, amount={} {}", developerId, amount, currency);
    }

    /**
     * 通知用户：新技能推荐
     */
    public void notifyNewSkillRecommendation(UUID userId, String skillName, String description) {
        String title = "为您推荐新技能";
        String content = String.format("「%s」：%s", skillName, description);
        sendInAppNotification(userId, "recommendation", title, content);
    }
}
