package com.qoobot.qooauth.apikey;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.qoobot.qooauth.apikey", "com.qoobot.qooauth.common"})
public class QooApiKeyApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooApiKeyApplication.class, args);
    }
}
