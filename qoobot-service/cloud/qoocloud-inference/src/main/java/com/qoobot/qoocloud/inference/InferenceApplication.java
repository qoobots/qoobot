package com.qoobot.qoocloud.inference;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * qoocloud-inference — 推理服务 (:8200)
 * 模型托管 / 推理 API (REST/gRPC) / 推理调度 / 推理缓存 / 端云混合路由 / Prompt 管理 / 推理审计
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class InferenceApplication {

    public static void main(String[] args) {
        SpringApplication.run(InferenceApplication.class, args);
    }
}
