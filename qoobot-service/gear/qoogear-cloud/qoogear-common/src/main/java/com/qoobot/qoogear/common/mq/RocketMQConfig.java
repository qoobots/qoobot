package com.qoobot.qoogear.common.mq;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.autoconfigure.RocketMQAutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.context.annotation.Configuration;

/**
 * RocketMQ message queue configuration.
 *
 * Defined Topics (per 04数据设计.md):
 *   cert-status-change     — certification application status transitions
 *   cert-issued             — new certificate issued
 *   standard-update         — standard specification created/updated
 *   developer-registered    — new developer registered
 *   lab-assignment-created  — new lab testing assignment
 *   security-audit-log      — security audit events
 *   fmea-alert              — FMEA risk level changes
 *   file-upload-complete    — MinIO file upload completion
 *
 * Consumers are defined in each service module.
 */
@Slf4j
@Configuration
@ConditionalOnClass(RocketMQAutoConfiguration.class)
public class RocketMQConfig {

    public static final String TOPIC_CERT_STATUS_CHANGE = "cert-status-change";
    public static final String TOPIC_CERT_ISSUED = "cert-issued";
    public static final String TOPIC_STANDARD_UPDATE = "standard-update";
    public static final String TOPIC_DEVELOPER_REGISTERED = "developer-registered";
    public static final String TOPIC_LAB_ASSIGNMENT_CREATED = "lab-assignment-created";
    public static final String TOPIC_SECURITY_AUDIT_LOG = "security-audit-log";
    public static final String TOPIC_FMEA_ALERT = "fmea-alert";
    public static final String TOPIC_FILE_UPLOAD_COMPLETE = "file-upload-complete";
}
