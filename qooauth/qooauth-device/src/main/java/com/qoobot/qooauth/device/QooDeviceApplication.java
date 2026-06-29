package com.qoobot.qooauth.device;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.device", "com.qoobot.qooauth.common"})
@EnableScheduling
public class QooDeviceApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooDeviceApplication.class, args);
    }
}
