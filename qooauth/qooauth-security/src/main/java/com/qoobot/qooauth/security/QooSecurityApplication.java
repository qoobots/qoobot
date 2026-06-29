package com.qoobot.qooauth.security;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.security", "com.qoobot.qooauth.common"})
public class QooSecurityApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooSecurityApplication.class, args);
    }
}
