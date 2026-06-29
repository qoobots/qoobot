package com.qoobot.qoogear.security.service;

import com.qoobot.qoogear.common.exception.QooGearException;
import com.qoobot.qoogear.security.domain.SecurityAudit;
import com.qoobot.qoogear.security.repository.SecurityAuditRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for SecurityAuditService.
 */
@ExtendWith(MockitoExtension.class)
class SecurityAuditServiceTest {

    @Mock private SecurityAuditRepository auditRepo;

    @InjectMocks
    private SecurityAuditService service;

    private SecurityAudit audit;

    @BeforeEach
    void setUp() {
        audit = new SecurityAudit();
        audit.setId(1L);
        audit.setApplicationId(100L);
        audit.setRiskLevel("medium");
        audit.setAuditorId(10L);
        audit.setStatus("pending");
    }

    @Test
    void shouldCreateAuditWithPendingStatus() {
        when(auditRepo.save(any(SecurityAudit.class))).thenAnswer(inv -> {
            SecurityAudit a = inv.getArgument(0);
            a.setId(1L);
            return a;
        });

        SecurityAudit newAudit = new SecurityAudit();
        newAudit.setApplicationId(200L);
        newAudit.setRiskLevel("low");
        newAudit.setAuditorId(10L);

        SecurityAudit result = service.createAudit(newAudit);
        assertNotNull(result);
        assertEquals("pending", result.getStatus());
        assertEquals("low", result.getRiskLevel());
    }

    @Test
    void shouldGetAuditById() {
        when(auditRepo.findById(1L)).thenReturn(Optional.of(audit));
        SecurityAudit result = service.getAudit(1L);
        assertNotNull(result);
        assertEquals(100L, result.getApplicationId());
    }

    @Test
    void shouldThrowWhenAuditNotFound() {
        when(auditRepo.findById(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getAudit(999L));
    }

    @Test
    void shouldGetAuditByApplicationId() {
        when(auditRepo.findByApplicationId(100L)).thenReturn(Optional.of(audit));
        SecurityAudit result = service.getAuditByApplication(100L);
        assertNotNull(result);
        assertEquals("medium", result.getRiskLevel());
    }

    @Test
    void shouldThrowWhenAuditNotFoundByApplicationId() {
        when(auditRepo.findByApplicationId(999L)).thenReturn(Optional.empty());
        assertThrows(QooGearException.class, () -> service.getAuditByApplication(999L));
    }

    @Test
    void shouldCompleteAudit() {
        when(auditRepo.findById(1L)).thenReturn(Optional.of(audit));
        when(auditRepo.save(any(SecurityAudit.class))).thenReturn(audit);

        SecurityAudit result = service.completeAudit(1L, "high",
                "Multiple safety vulnerabilities found in communication protocol",
                "Implement end-to-end encryption and authentication");

        assertEquals("completed", result.getStatus());
        assertEquals("high", result.getRiskLevel());
        assertNotNull(result.getFindings());
        assertNotNull(result.getRecommendation());
        assertNotNull(result.getCompletedAt());
    }

    @Test
    void shouldUpdateFmeaJson() {
        String fmeaJson = """
            {
              "failureModes": [
                {"mode": "通信中断", "severity": 8, "occurrence": 3, "detection": 2, "rpn": 48},
                {"mode": "认证芯片故障", "severity": 9, "occurrence": 2, "detection": 3, "rpn": 54}
              ]
            }""";

        when(auditRepo.findById(1L)).thenReturn(Optional.of(audit));
        when(auditRepo.save(any(SecurityAudit.class))).thenReturn(audit);

        SecurityAudit result = service.updateFmea(1L, fmeaJson);
        assertNotNull(result.getFmeaJson());
        assertTrue(result.getFmeaJson().contains("failureModes"));
    }

    @Test
    void shouldCountByRiskLevel() {
        when(auditRepo.countByRiskLevel("high")).thenReturn(5L);
        long count = service.countByRiskLevel("high");
        assertEquals(5L, count);
    }

    @Test
    void shouldCountByRiskLevelZero() {
        when(auditRepo.countByRiskLevel("critical")).thenReturn(0L);
        long count = service.countByRiskLevel("critical");
        assertEquals(0L, count);
    }
}
