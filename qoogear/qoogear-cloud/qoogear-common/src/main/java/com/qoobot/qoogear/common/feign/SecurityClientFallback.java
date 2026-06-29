package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Fallback for SecurityClient when qoogear-security service is unavailable.
 */
@Slf4j
@Component
public class SecurityClientFallback implements SecurityClient {

    @Override
    public ApiResponse<Map<String, Object>> createAuditEntry(Map<String, Object> auditEntry) {
        log.warn("SecurityClient.createAuditEntry fallback");
        return ApiResponse.error(503, "Security service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> queryAuditLogs(String entityType, Long entityId, int page, int size) {
        log.warn("SecurityClient.queryAuditLogs fallback");
        return ApiResponse.error(503, "Security service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> createFmeaRecord(Map<String, Object> fmea) {
        log.warn("SecurityClient.createFmeaRecord fallback");
        return ApiResponse.error(503, "Security service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> getFmeaRecord(Long id) {
        log.warn("SecurityClient.getFmeaRecord fallback: id={}", id);
        return ApiResponse.error(503, "Security service unavailable");
    }
}
