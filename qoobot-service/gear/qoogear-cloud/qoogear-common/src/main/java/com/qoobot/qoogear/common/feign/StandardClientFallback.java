package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Fallback for StandardClient when qoogear-standard service is unavailable.
 */
@Slf4j
@Component
public class StandardClientFallback implements StandardClient {

    @Override
    public ApiResponse<Map<String, Object>> getSpecification(Long id) {
        log.warn("StandardClient.getSpecification fallback: id={}", id);
        return ApiResponse.error(503, "Standard service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> listSpecifications(String category, int page, int size) {
        log.warn("StandardClient.listSpecifications fallback");
        return ApiResponse.error(503, "Standard service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> getTestChecklist(Long specId) {
        log.warn("StandardClient.getTestChecklist fallback: specId={}", specId);
        return ApiResponse.error(503, "Standard service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> checkCompatibility(String productCategory, String robotModel) {
        log.warn("StandardClient.checkCompatibility fallback");
        return ApiResponse.error(503, "Standard service unavailable");
    }
}
