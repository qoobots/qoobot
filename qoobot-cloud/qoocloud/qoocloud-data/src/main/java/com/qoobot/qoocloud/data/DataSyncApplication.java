package com.qoobot.qoocloud.data;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

/**
 * qoocloud-data — 数据同步服务 (:8203)
 * 经验回放同步、知识库共享、联邦学习聚合、数据管道、隐私过滤、数据治理
 */
@SpringBootApplication
@EnableDiscoveryClient
public class DataSyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(DataSyncApplication.class, args);
    }
}
