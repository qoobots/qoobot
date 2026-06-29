package com.qoobot.qooauth.audit;

import com.qoobot.qooauth.audit.entity.AuditLog;
import com.qoobot.qooauth.audit.service.LogIntegrityService;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class LogIntegrityServiceTest {

    private final LogIntegrityService service = new LogIntegrityService(null, null);

    @Test
    void computeMerkleRoot_emptyList_shouldReturnZeroHash() {
        String root = service.computeMerkleRoot(List.of());
        assertEquals("0".repeat(64), root);
    }

    @Test
    void computeMerkleRoot_singleEvent_shouldReturnConsistentHash() {
        AuditLog log = createLog("event-1", "hash-1");
        String root1 = service.computeMerkleRoot(List.of(log));
        String root2 = service.computeMerkleRoot(List.of(log));

        assertEquals(root1, root2, "Merkle root should be deterministic");
        assertEquals(64, root1.length());
    }

    @Test
    void computeMerkleRoot_multipleEvents_shouldReturnDifferentHashForDifferentOrder() {
        AuditLog log1 = createLog("event-1", "hash-1");
        AuditLog log2 = createLog("event-2", "hash-2");

        String root12 = service.computeMerkleRoot(List.of(log1, log2));
        String root21 = service.computeMerkleRoot(List.of(log2, log1));

        assertNotEquals(root12, root21, "Merkle root should be order-dependent");
    }

    @Test
    void computeMerkleRoot_oddNumberOfEvents_shouldHandleCorrectly() {
        AuditLog log1 = createLog("event-1", "hash-1");
        AuditLog log2 = createLog("event-2", "hash-2");
        AuditLog log3 = createLog("event-3", "hash-3");

        String root = service.computeMerkleRoot(List.of(log1, log2, log3));
        assertNotNull(root);
        assertEquals(64, root.length());
    }

    @Test
    void computeMerkleRoot_powerOfTwo_shouldWork() {
        List<AuditLog> logs = new ArrayList<>();
        for (int i = 0; i < 8; i++) {
            logs.add(createLog("event-" + i, "hash-" + i));
        }

        String root = service.computeMerkleRoot(logs);
        assertNotNull(root);
        assertEquals(64, root.length());
    }

    @Test
    void computeMerkleRoot_tamperDetection_shouldProduceDifferentHash() {
        AuditLog log1 = createLog("event-1", "hash-1");
        AuditLog log2 = createLog("event-2", "hash-2");

        String root = service.computeMerkleRoot(List.of(log1, log2));

        // Tamper with log2
        AuditLog tamperedLog = createLog("event-2", "hash-2-modified");
        String tamperedRoot = service.computeMerkleRoot(List.of(log1, tamperedLog));

        assertNotEquals(root, tamperedRoot, "Tampered data should produce different Merkle root");
    }

    private AuditLog createLog(String eventId, String integrityHash) {
        return AuditLog.builder()
                .eventId(UUID.nameUUIDFromBytes(eventId.getBytes()))
                .eventTime(Instant.now())
                .actorType("USER")
                .actorId("user-001")
                .action("LOGIN")
                .result("SUCCESS")
                .integrityHash(integrityHash)
                .build();
    }
}
