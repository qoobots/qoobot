package com.qoobot.qooauth.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class QooAuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooAuthApplication.class, args);
    }
}
