package com.qoobot.qooauth.robot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.robot", "com.qoobot.qooauth.common"})
public class QooRobotTrustApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooRobotTrustApplication.class, args);
    }
}
