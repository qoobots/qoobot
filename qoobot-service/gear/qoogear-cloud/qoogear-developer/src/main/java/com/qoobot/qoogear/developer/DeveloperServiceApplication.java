package com.qoobot.qoogear.developer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoogear"})
@EnableDiscoveryClient
public class DeveloperServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DeveloperServiceApplication.class, args);
    }
}
