package com.qoobot.qoocloud.twin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-twin — 数字孪生服务 (:8205)
 * 环境镜像 / 行为仿真 / 异常推演 / 回放分析 / 场景库
 */
@SpringBootApplication
@EnableDiscoveryClient
public class TwinApplication {

    public static void main(String[] args) {
        SpringApplication.run(TwinApplication.class, args);
    }
}
