package com.qoobot.qooauth.audit.repository;

import com.qoobot.qooauth.audit.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long>, JpaSpecificationExecutor<AuditLog> {

    /**
     * Find audit events by actor within time range.
     */
    @Query("SELECT a FROM AuditLog a WHERE a.actorType = :actorType AND a.actorId = :actorId " +
           "AND a.eventTime BETWEEN :startTime AND :endTime ORDER BY a.eventTime DESC")
    Page<AuditLog> findByActor(@Param("actorType") String actorType,
                                @Param("actorId") String actorId,
                                @Param("startTime") Instant startTime,
                                @Param("endTime") Instant endTime,
                                Pageable pageable);

    /**
     * Find audit events by session.
     */
    Page<AuditLog> findBySessionIdOrderByEventTimeDesc(String sessionId, Pageable pageable);

    /**
     * Find audit events by trace ID.
     */
    List<AuditLog> findByTraceIdOrderByEventTimeDesc(String traceId);

    /**
     * Find audit events by event ID (exact match).
     */
    List<AuditLog> findByEventId(UUID eventId);

    /**
     * Count events by action within time range (for analytics).
     */
    @Query("SELECT a.action, COUNT(a) FROM AuditLog a WHERE a.eventTime BETWEEN :startTime AND :endTime " +
           "GROUP BY a.action ORDER BY COUNT(a) DESC")
    List<Object[]> countByAction(@Param("startTime") Instant startTime, @Param("endTime") Instant endTime);

    /**
     * Count failed events by actor within time range.
     */
    @Query("SELECT a.actorId, COUNT(a) FROM AuditLog a WHERE a.result = 'FAILURE' " +
           "AND a.eventTime BETWEEN :startTime AND :endTime " +
           "GROUP BY a.actorId HAVING COUNT(a) >= :threshold ORDER BY COUNT(a) DESC")
    List<Object[]> findActorsExceedingFailureThreshold(@Param("startTime") Instant startTime,
                                                        @Param("endTime") Instant endTime,
                                                        @Param("threshold") long threshold);

    /**
     * Find events within a time bucket (for integrity chain computation).
     */
    @Query("SELECT a FROM AuditLog a WHERE a.eventTime >= :bucketStart AND a.eventTime < :bucketEnd " +
           "ORDER BY a.eventTime ASC, a.id ASC")
    List<AuditLog> findEventsInBucket(@Param("bucketStart") Instant bucketStart,
                                       @Param("bucketEnd") Instant bucketEnd);

    /**
     * Delete events older than retention period.
     */
    @Query(value = "DELETE FROM audit_logs WHERE event_time < :cutoffTime", nativeQuery = true)
    int deleteEventsOlderThan(@Param("cutoffTime") Instant cutoffTime);
}
