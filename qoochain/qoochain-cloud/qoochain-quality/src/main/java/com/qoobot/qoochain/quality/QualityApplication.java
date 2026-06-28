package com.qoobot.qoochain.quality;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoochain.quality", "com.qoobot.qoochain.common"})
public class QualityApplication {
    public static void main(String[] args) {
        SpringApplication.run(QualityApplication.class, args);
    }
}
