package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Fallback for LabClient when qoogear-lab service is unavailable.
 */
@Slf4j
@Component
public class LabClientFallback implements LabClient {

    @Override
    public ApiResponse<Map<String, Object>> createAssignment(Map<String, Object> assignment) {
        log.warn("LabClient.createAssignment fallback");
        return ApiResponse.error(503, "Lab service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> getAssignment(Long id) {
        log.warn("LabClient.getAssignment fallback: id={}", id);
        return ApiResponse.error(503, "Lab service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> submitTestResults(Long id, Map<String, Object> results) {
        log.warn("LabClient.submitTestResults fallback: id={}", id);
        return ApiResponse.error(503, "Lab service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> listEquipment() {
        log.warn("LabClient.listEquipment fallback");
        return ApiResponse.error(503, "Lab service unavailable");
    }
}
