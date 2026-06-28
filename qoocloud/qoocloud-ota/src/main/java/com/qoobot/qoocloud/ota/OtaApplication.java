package com.qoobot.qoocloud.ota;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-ota — OTA 升级服务 (:8202)
 * 固件/模型/技能升级 / 灰度发布 / 增量更新 / 自动回滚 / 升级策略
 */
@SpringBootApplication
@EnableDiscoveryClient
public class OtaApplication {

    public static void main(String[] args) {
        SpringApplication.run(OtaApplication.class, args);
    }
}
