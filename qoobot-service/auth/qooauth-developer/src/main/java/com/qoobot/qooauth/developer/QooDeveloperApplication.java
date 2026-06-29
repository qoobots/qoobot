package com.qoobot.qooauth.developer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.developer", "com.qoobot.qooauth.common"})
public class QooDeveloperApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooDeveloperApplication.class, args);
    }
}
