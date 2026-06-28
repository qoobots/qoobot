package com.qoobot.qoocloud.teleop;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * qoocloud-teleop — 远程遥控服务 (:8208)
 *
 * WebRTC 信令中继 / 控制指令低延迟转发 / 视频流转发 (SFU) /
 * 遥控会话生命周期管理 / 示教数据采集与存储
 *
 * 对标: Android Accessibility Service + Device Policy + 远程桌面
 */
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
@EnableScheduling
public class TeleopApplication {

    public static void main(String[] args) {
        SpringApplication.run(TeleopApplication.class, args);
    }
}
