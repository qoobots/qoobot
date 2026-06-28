package com.qoobot.qoogear.cert;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoogear"})
@EnableDiscoveryClient
public class CertApplication {
    public static void main(String[] args) {
        SpringApplication.run(CertApplication.class, args);
    }
}
