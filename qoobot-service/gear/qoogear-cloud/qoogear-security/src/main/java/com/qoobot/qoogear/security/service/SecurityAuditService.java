package com.qoobot.qoogear.security.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.security.domain.*;
import com.qoobot.qoogear.security.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.ZonedDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class SecurityAuditService {

    private final SecurityAuditRepository auditRepo;

    @Transactional
    public SecurityAudit createAudit(SecurityAudit audit) {
        audit.setStatus("pending");
        return auditRepo.save(audit);
    }

    public SecurityAudit getAudit(Long id) {
        return auditRepo.findById(id)
                .orElseThrow(() -> QooGearException.notFound("SecurityAudit", id));
    }

    public SecurityAudit getAuditByApplication(Long appId) {
        return auditRepo.findByApplicationId(appId)
                .orElseThrow(() -> QooGearException.notFound("SecurityAudit for application", appId));
    }

    @Transactional
    public SecurityAudit completeAudit(Long id, String riskLevel, String findings, String recommendation) {
        SecurityAudit audit = getAudit(id);
        audit.setRiskLevel(riskLevel);
        audit.setFindings(findings);
        audit.setRecommendation(recommendation);
        audit.setStatus("completed");
        audit.setCompletedAt(ZonedDateTime.now());
        return auditRepo.save(audit);
    }

    @Transactional
    public SecurityAudit updateFmea(Long id, String fmeaJson) {
        SecurityAudit audit = getAudit(id);
        audit.setFmeaJson(fmeaJson);
        return auditRepo.save(audit);
    }

    public long countByRiskLevel(String riskLevel) {
        return auditRepo.countByRiskLevel(riskLevel);
    }
}
