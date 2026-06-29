package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.Map;

/**
 * Feign client for qoogear-cert service (port 8091).
 */
@FeignClient(name = "qoogear-cert", path = "/api/v1/cert")
public interface CertificationClient {

    @GetMapping("/applications/{id}")
    ApiResponse<Map<String, Object>> getApplication(@PathVariable("id") Long id);

    @PostMapping("/applications/{id}/status")
    ApiResponse<Map<String, Object>> updateApplicationStatus(
            @PathVariable("id") Long id,
            @RequestBody Map<String, Object> statusUpdate);

    @GetMapping("/certificates/{id}")
    ApiResponse<Map<String, Object>> getCertificate(@PathVariable("id") Long id);

    @GetMapping("/certificates/validate/{certNumber}")
    ApiResponse<Map<String, Object>> validateCertificate(@PathVariable("certNumber") String certNumber);
}
