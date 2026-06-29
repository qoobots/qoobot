package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Fallback for CertificationClient when qoogear-cert service is unavailable.
 */
@Slf4j
@Component
public class CertificationClientFallback implements CertificationClient {

    @Override
    public ApiResponse<Map<String, Object>> getApplication(Long id) {
        log.warn("CertificationClient.getApplication fallback: id={}", id);
        return ApiResponse.error(503, "Certification service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> updateApplicationStatus(Long id, Map<String, Object> statusUpdate) {
        log.warn("CertificationClient.updateApplicationStatus fallback: id={}", id);
        return ApiResponse.error(503, "Certification service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> getCertificate(Long id) {
        log.warn("CertificationClient.getCertificate fallback: id={}", id);
        return ApiResponse.error(503, "Certification service unavailable");
    }

    @Override
    public ApiResponse<Map<String, Object>> validateCertificate(String certNumber) {
        log.warn("CertificationClient.validateCertificate fallback: certNumber={}", certNumber);
        return ApiResponse.error(503, "Certification service unavailable");
    }
}
