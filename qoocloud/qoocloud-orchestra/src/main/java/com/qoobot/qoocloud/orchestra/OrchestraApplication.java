package com.qoobot.qoocloud.orchestra;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-orchestra — 多机器人编排服务 (:8204)
 * 集群管理 / 任务分配 / 协作调度 / 资源优化 / 场景编排 / 监控面板
 */
@SpringBootApplication
@EnableDiscoveryClient
public class OrchestraApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrchestraApplication.class, args);
    }
}
