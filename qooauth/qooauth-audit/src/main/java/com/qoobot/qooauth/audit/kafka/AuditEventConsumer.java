package com.qoobot.qooauth.audit.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qooauth.audit.dto.AuditEventRequest;
import com.qoobot.qooauth.audit.service.AuditService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Kafka consumer for audit events published by other qooauth services.
 * <p>
 * Uses batch consumption with manual acknowledgment for reliability.
 * Accumulates events up to batch.size before flushing to database.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuditEventConsumer {

    private final AuditService auditService;
    private final ObjectMapper objectMapper;

    private static final int BATCH_SIZE = 200;
    private static final long BATCH_TIMEOUT_MS = 5000;

    private final List<AuditEventRequest> buffer = new ArrayList<>();
    private long lastFlushTime = System.currentTimeMillis();

    /**
     * Consume audit events from Kafka topic "qooauth.audit.events".
     */
    @KafkaListener(
            topics = "qooauth.audit.events",
            containerFactory = "auditKafkaListenerContainerFactory"
    )
    public void consume(List<ConsumerRecord<String, String>> records, Acknowledgment ack) {
        log.debug("Received {} audit events from Kafka", records.size());

        int parsedCount = 0;
        int errorCount = 0;

        for (ConsumerRecord<String, String> record : records) {
            try {
                AuditEventRequest event = objectMapper.readValue(record.value(), AuditEventRequest.class);
                synchronized (buffer) {
                    buffer.add(event);
                }
                parsedCount++;
            } catch (Exception e) {
                log.error("Failed to parse audit event from Kafka: offset={}, error={}",
                        record.offset(), e.getMessage());
                errorCount++;
            }
        }

        // Flush if batch size reached or timeout elapsed
        synchronized (buffer) {
            long elapsed = System.currentTimeMillis() - lastFlushTime;
            if (buffer.size() >= BATCH_SIZE || elapsed >= BATCH_TIMEOUT_MS) {
                flushBuffer();
            }
        }

        // Acknowledge after successful parsing (events buffered for batch write)
        ack.acknowledge();

        if (errorCount > 0) {
            log.warn("Audit event parsing: {} succeeded, {} failed (skipped)", parsedCount, errorCount);
        }
    }

    /**
     * Periodic flush for events that haven't reached batch size within timeout.
     */
    @org.springframework.scheduling.annotation.Scheduled(fixedDelay = 60000)
    public void scheduledFlush() {
        synchronized (buffer) {
            if (!buffer.isEmpty()) {
                flushBuffer();
            }
        }
    }

    private void flushBuffer() {
        if (buffer.isEmpty()) return;

        List<AuditEventRequest> batch = new ArrayList<>(buffer);
        buffer.clear();
        lastFlushTime = System.currentTimeMillis();

        try {
            auditService.writeAuditEvents(batch);
            log.debug("Flushed {} audit events to database", batch.size());
        } catch (Exception e) {
            log.error("Failed to flush audit events batch: {}", e.getMessage(), e);
            // Re-add to buffer for retry on next flush
            buffer.addAll(0, batch);
        }
    }
}
