package com.qoobot.qoogear.standard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoogear"})
@EnableDiscoveryClient
public class StandardApplication {
    public static void main(String[] args) {
        SpringApplication.run(StandardApplication.class, args);
    }
}
