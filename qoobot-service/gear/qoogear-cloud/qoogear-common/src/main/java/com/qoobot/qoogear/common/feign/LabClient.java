package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.Map;

/**
 * Feign client for qoogear-lab service (port 8094).
 */
@FeignClient(name = "qoogear-lab", path = "/api/v1/lab", fallback = LabClientFallback.class)
public interface LabClient {

    @PostMapping("/assignments")
    ApiResponse<Map<String, Object>> createAssignment(@RequestBody Map<String, Object> assignment);

    @GetMapping("/assignments/{id}")
    ApiResponse<Map<String, Object>> getAssignment(@PathVariable("id") Long id);

    @PostMapping("/assignments/{id}/results")
    ApiResponse<Map<String, Object>> submitTestResults(
            @PathVariable("id") Long id,
            @RequestBody Map<String, Object> results);

    @GetMapping("/equipment")
    ApiResponse<Map<String, Object>> listEquipment();
}
