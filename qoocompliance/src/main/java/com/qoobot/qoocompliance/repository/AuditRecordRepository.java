package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.AuditRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AuditRecordRepository extends JpaRepository<AuditRecord, Long> {

    List<AuditRecord> findByProductId(String productId);

    List<AuditRecord> findByAction(String action);

    List<AuditRecord> findByUserId(String userId);

    List<AuditRecord> findByProductIdAndAction(String productId, String action);

    List<AuditRecord> findByMarket(String market);
}
