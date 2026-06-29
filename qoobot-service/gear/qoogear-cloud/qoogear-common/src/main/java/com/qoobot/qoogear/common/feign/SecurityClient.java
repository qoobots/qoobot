package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Feign client for qoogear-security service (port 8095).
 */
@FeignClient(name = "qoogear-security", path = "/api/v1/security", fallback = SecurityClientFallback.class)
public interface SecurityClient {

    @PostMapping("/audit")
    ApiResponse<Map<String, Object>> createAuditEntry(@RequestBody Map<String, Object> auditEntry);

    @GetMapping("/audit")
    ApiResponse<Map<String, Object>> queryAuditLogs(
            @RequestParam(value = "entityType", required = false) String entityType,
            @RequestParam(value = "entityId", required = false) Long entityId,
            @RequestParam(value = "page", defaultValue = "0") int page,
            @RequestParam(value = "size", defaultValue = "20") int size);

    @PostMapping("/fmea")
    ApiResponse<Map<String, Object>> createFmeaRecord(@RequestBody Map<String, Object> fmea);

    @GetMapping("/fmea/{id}")
    ApiResponse<Map<String, Object>> getFmeaRecord(@PathVariable("id") Long id);
}
