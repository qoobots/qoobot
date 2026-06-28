package com.qoobot.qooauth.audit;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * QooAuth Audit &amp; Compliance Service.
 * <p>
 * Handles audit event ingestion (via Kafka), persistent storage
 * (PostgreSQL partitioned tables), query APIs, compliance report
 * generation, and log integrity verification.
 */
@SpringBootApplication(scanBasePackages = "com.qoobot.qooauth")
@EnableScheduling
public class QooAuditApplication {

    public static void main(String[] args) {
        SpringApplication.run(QooAuditApplication.class, args);
    }
}
