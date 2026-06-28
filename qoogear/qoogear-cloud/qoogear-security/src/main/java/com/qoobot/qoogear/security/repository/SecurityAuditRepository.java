package com.qoobot.qoogear.security.repository;

import com.qoobot.qoogear.security.domain.SecurityAudit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface SecurityAuditRepository extends JpaRepository<SecurityAudit, Long> {
    Optional<SecurityAudit> findByApplicationId(Long applicationId);
    long countByRiskLevel(String riskLevel);
}
