package com.qoobot.qooauth.audit;

import com.qoobot.qooauth.audit.dto.AuditEventRequest;
import com.qoobot.qooauth.audit.dto.AuditQueryRequest;
import com.qoobot.qooauth.audit.dto.AuditQueryResponse;
import com.qoobot.qooauth.audit.entity.AuditLog;
import com.qoobot.qooauth.audit.repository.AuditLogRepository;
import com.qoobot.qooauth.audit.service.AuditService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuditServiceTest {

    @Mock
    private AuditLogRepository auditLogRepository;

    @Mock
    private com.fasterxml.jackson.databind.ObjectMapper objectMapper;

    @InjectMocks
    private AuditService auditService;

    private AuditEventRequest sampleRequest;

    @BeforeEach
    void setUp() {
        sampleRequest = AuditEventRequest.builder()
                .eventId(UUID.randomUUID())
                .eventTime(Instant.now())
                .actorType("USER")
                .actorId("user-001")
                .actorName("testuser")
                .action("LOGIN")
                .resourceType("USER")
                .resourceId("user-001")
                .result("SUCCESS")
                .clientIp("192.168.1.1")
                .userAgent("Mozilla/5.0")
                .sessionId("sess-abc123")
                .build();
    }

    @Test
    void writeAuditEvent_shouldSetIntegrityHash() {
        AuditLog savedLog = AuditLog.builder()
                .eventId(sampleRequest.getEventId())
                .eventTime(sampleRequest.getEventTime())
                .actorType(sampleRequest.getActorType())
                .actorId(sampleRequest.getActorId())
                .action(sampleRequest.getAction())
                .result(sampleRequest.getResult())
                .clientIp(sampleRequest.getClientIp())
                .build();

        when(auditLogRepository.save(any(AuditLog.class))).thenReturn(savedLog);

        AuditLog result = auditService.writeAuditEvent(sampleRequest);

        assertNotNull(result);
        verify(auditLogRepository, times(1)).save(any(AuditLog.class));

        // Verify integrity hash is set on the saved entity
        ArgumentCaptor<AuditLog> captor = ArgumentCaptor.forClass(AuditLog.class);
        verify(auditLogRepository).save(captor.capture());
        assertNotNull(captor.getValue().getIntegrityHash());
        assertEquals(64, captor.getValue().getIntegrityHash().length());
    }

    @Test
    void writeAuditEvents_shouldBatchSave() {
        when(auditLogRepository.saveAll(anyList())).thenReturn(List.of());

        List<AuditEventRequest> requests = List.of(sampleRequest,
                sampleRequest.toBuilder().eventId(UUID.randomUUID()).build());

        List<AuditLog> results = auditService.writeAuditEvents(requests);

        assertNotNull(results);
        verify(auditLogRepository, times(1)).saveAll(anyList());
    }

    @Test
    void queryAuditLogs_shouldReturnPaginatedResults() {
        AuditLog log = AuditLog.builder()
                .eventId(sampleRequest.getEventId())
                .eventTime(sampleRequest.getEventTime())
                .actorType(sampleRequest.getActorType())
                .actorId(sampleRequest.getActorId())
                .action(sampleRequest.getAction())
                .result(sampleRequest.getResult())
                .clientIp(sampleRequest.getClientIp())
                .build();

        Page<AuditLog> page = new PageImpl<>(List.of(log));

        @SuppressWarnings("unchecked")
        Specification<AuditLog> spec = any(Specification.class);
        when(auditLogRepository.findAll(spec, any(Pageable.class))).thenReturn(page);

        AuditQueryRequest queryRequest = AuditQueryRequest.builder()
                .actorType("USER")
                .actorId("user-001")
                .page(0)
                .size(50)
                .build();

        AuditQueryResponse response = auditService.queryAuditLogs(queryRequest);

        assertNotNull(response);
        assertEquals(1, response.getTotalCount());
        assertEquals(1, response.getEvents().size());
        assertEquals("LOGIN", response.getEvents().get(0).getAction());
    }
}
