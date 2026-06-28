package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.dto.response.DashboardResponse;
import com.qoobot.qoostore.service.AnalyticsService;
import com.qoobot.qoostore.service.PayoutService;
import com.qoobot.qoostore.entity.DeveloperPayout;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/analytics")
@RequiredArgsConstructor
@Tag(name = "运营分析", description = "开发者仪表板/平台运营/排行")
public class AnalyticsController {

    private final AnalyticsService analyticsService;
    private final PayoutService payoutService;

    @GetMapping("/platform/overview")
    @Operation(summary = "平台总览")
    public ApiResponse<DashboardResponse> getPlatformOverview() {
        return ApiResponse.success(analyticsService.getPlatformOverview());
    }

    @GetMapping("/developers/{developerId}/dashboard")
    @Operation(summary = "开发者仪表板")
    public ApiResponse<Map<String, Object>> getDeveloperDashboard(@PathVariable Long developerId) {
        return ApiResponse.success(analyticsService.getDeveloperDashboard(developerId));
    }

    @GetMapping("/developers/{developerId}/revenue")
    @Operation(summary = "开发者收益")
    public ApiResponse<BigDecimal> getDeveloperRevenue(
            @PathVariable Long developerId,
            @RequestParam LocalDate startDate,
            @RequestParam LocalDate endDate) {
        return ApiResponse.success(analyticsService.getDeveloperRevenue(developerId, startDate, endDate));
    }

    @PostMapping("/developers/{developerId}/payouts")
    @Operation(summary = "发起结算")
    public ApiResponse<DeveloperPayout> createPayout(
            @PathVariable Long developerId,
            @RequestParam String payoutMethod) {
        return ApiResponse.success(payoutService.createPayout(developerId, payoutMethod));
    }

    @GetMapping("/developers/{developerId}/payouts")
    @Operation(summary = "结算记录")
    public ApiResponse<List<DeveloperPayout>> getPayouts(@PathVariable Long developerId) {
        return ApiResponse.success(payoutService.getPayouts(developerId));
    }
}
