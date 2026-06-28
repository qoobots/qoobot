package com.qoobot.qoochain.aftermarket;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qoochain.aftermarket", "com.qoobot.qoochain.common"})
public class AftermarketApplication {
    public static void main(String[] args) {
        SpringApplication.run(AftermarketApplication.class, args);
    }
}
