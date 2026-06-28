package com.qoobot.qoochain.bom;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoochain.bom", "com.qoobot.qoochain.common"})
public class BomApplication {
    public static void main(String[] args) {
        SpringApplication.run(BomApplication.class, args);
    }
}
