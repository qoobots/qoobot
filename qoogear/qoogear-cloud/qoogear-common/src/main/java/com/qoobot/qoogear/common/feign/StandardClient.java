package com.qoobot.qoogear.common.feign;

import com.qoobot.qoogear.common.dto.ApiResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Map;

/**
 * Feign client for qoogear-standard service (port 8092).
 */
@FeignClient(name = "qoogear-standard", path = "/api/v1/standard", fallback = StandardClientFallback.class)
public interface StandardClient {

    @GetMapping("/specs/{id}")
    ApiResponse<Map<String, Object>> getSpecification(@PathVariable("id") Long id);

    @GetMapping("/specs")
    ApiResponse<Map<String, Object>> listSpecifications(
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "page", defaultValue = "0") int page,
            @RequestParam(value = "size", defaultValue = "20") int size);

    @GetMapping("/checklist/{specId}")
    ApiResponse<Map<String, Object>> getTestChecklist(@PathVariable("specId") Long specId);

    @GetMapping("/compatibility")
    ApiResponse<Map<String, Object>> checkCompatibility(
            @RequestParam("productCategory") String productCategory,
            @RequestParam("robotModel") String robotModel);
}
