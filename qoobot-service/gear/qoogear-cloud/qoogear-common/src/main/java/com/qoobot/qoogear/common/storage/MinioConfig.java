package com.qoobot.qoogear.common.storage;

import io.minio.MinioClient;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * MinIO object storage configuration.
 *
 * Bucket structure (per 04数据设计.md):
 *   qoogear-documents/    — certification documents (PDF reports, certificates)
 *   qoogear-firmware/      — accessory firmware files
 *   qoogear-sdk/           — SDK distribution packages
 *   qoogear-designs/       — reference design files
 *   qoogear-test-results/  — lab test result attachments
 *   qoogear-fmea/          — FMEA analysis reports
 *   qoogear-public/        — public assets (logos, datasheets)
 */
@Slf4j
@Configuration
@ConfigurationProperties(prefix = "qoogear.storage.minio")
@Data
public class MinioConfig {

    private String endpoint = "http://localhost:9000";
    private String accessKey = "minioadmin";
    private String secretKey = "minioadmin";
    private String region = "us-east-1";
    private boolean secure = false;

    @Bean
    public MinioClient minioClient() {
        log.info("Initializing MinIO client: endpoint={}, region={}", endpoint, region);
        return MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                .region(region)
                .build();
    }

    // Bucket name constants
    public static final String BUCKET_DOCUMENTS = "qoogear-documents";
    public static final String BUCKET_FIRMWARE = "qoogear-firmware";
    public static final String BUCKET_SDK = "qoogear-sdk";
    public static final String BUCKET_DESIGNS = "qoogear-designs";
    public static final String BUCKET_TEST_RESULTS = "qoogear-test-results";
    public static final String BUCKET_FMEA = "qoogear-fmea";
    public static final String BUCKET_PUBLIC = "qoogear-public";
}
