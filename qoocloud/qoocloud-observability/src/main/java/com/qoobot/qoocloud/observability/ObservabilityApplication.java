package com.qoobot.qoocloud.observability;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-observability — 可观测性服务 (:8206)
 * 全链路追踪 / 日志聚合 / 智能告警 / SLA 监控 / 用量仪表板
 */
@SpringBootApplication
@EnableDiscoveryClient
public class ObservabilityApplication {

    public static void main(String[] args) {
        SpringApplication.run(ObservabilityApplication.class, args);
    }
}
