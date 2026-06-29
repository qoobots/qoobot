package com.qoobot.qooauth.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.gateway", "com.qoobot.qooauth.common"})
public class QooGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooGatewayApplication.class, args);
    }
}
