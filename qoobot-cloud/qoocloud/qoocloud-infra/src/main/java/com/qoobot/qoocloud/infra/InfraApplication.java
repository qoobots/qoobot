package com.qoobot.qoocloud.infra;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-infra — 云基础设施服务 (:8207)
 * 多租户隔离 / 弹性伸缩 / 多区域部署 / 灾备恢复 / API 网关
 */
@SpringBootApplication
@EnableDiscoveryClient
public class InfraApplication {

    public static void main(String[] args) {
        SpringApplication.run(InfraApplication.class, args);
    }
}
