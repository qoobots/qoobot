package com.qoobot.qoochain.line;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoochain.line", "com.qoobot.qoochain.common"})
public class LineApplication {
    public static void main(String[] args) {
        SpringApplication.run(LineApplication.class, args);
    }
}
