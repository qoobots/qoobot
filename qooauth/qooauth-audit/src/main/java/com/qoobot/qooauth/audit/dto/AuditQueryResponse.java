package com.qoobot.qooauth.audit.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditQueryResponse {

    private List<AuditLogEntry> events;
    private long totalCount;
    private int page;
    private int size;
    private int totalPages;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AuditLogEntry {
        private Long id;
        private String eventId;
        private String eventTime;
        private String actorType;
        private String actorId;
        private String actorName;
        private String action;
        private String resourceType;
        private String resourceId;
        private String resourceName;
        private String result;
        private String errorCode;
        private String clientIp;
        private String userAgent;
        private String geoCountry;
        private String geoCity;
        private String sessionId;
        private String clientId;
        private String authMethod;
        private Object details;
        private String traceId;
        private String integrityHash;
    }
}
