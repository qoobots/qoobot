package com.qoobot.qooauth.security.repository;

import com.qoobot.qooauth.security.entity.SecurityEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

/**
 * Repository for SecurityEvent entity.
 */
@Repository
public interface SecurityEventRepository extends JpaRepository<SecurityEvent, Long> {

    /**
     * Find security events for a user.
     */
    List<SecurityEvent> findByUserIdOrderByDetectedAtDesc(String userId);

    /**
     * Find security events by event type.
     */
    List<SecurityEvent> findByEventTypeOrderByDetectedAtDesc(String eventType);

    /**
     * Find security events by severity level.
     */
    List<SecurityEvent> findBySeverityOrderByDetectedAtDesc(String severity);

    /**
     * Find unresolved security events (resolved_at IS NULL).
     */
    List<SecurityEvent> findByResolvedAtIsNullOrderByDetectedAtDesc();

    /**
     * Find events detected within a time range.
     */
    List<SecurityEvent> findByDetectedAtBetweenOrderByDetectedAtDesc(Instant startTime, Instant endTime);
}
