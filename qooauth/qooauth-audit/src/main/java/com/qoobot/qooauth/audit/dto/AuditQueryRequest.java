package com.qoobot.qooauth.audit.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditQueryRequest {

    private String actorType;
    private String actorId;
    private String action;
    private String resourceType;
    private String resourceId;
    private String result;
    private String clientIp;
    private String sessionId;
    private String traceId;

    private Instant startTime;
    private Instant endTime;

    @Min(0)
    @Builder.Default
    private int page = 0;

    @Min(1)
    @Max(1000)
    @Builder.Default
    private int size = 50;

    private String sortBy = "eventTime";
    private String sortDirection = "DESC";
}
