package com.qoobot.qoogear.security.repository;

import com.qoobot.qoogear.security.domain.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.time.ZonedDateTime;
import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    List<AuditLog> findByResourceTypeAndResourceId(String resourceType, Long resourceId);
    List<AuditLog> findByActor(String actor);
    Page<AuditLog> findByCreatedBetween(ZonedDateTime start, ZonedDateTime end, Pageable pageable);
}
