package com.qoobot.qoostore.controller;

import com.qoobot.qoostore.dto.response.ApiResponse;
import com.qoobot.qoostore.dto.response.OrderResponse;
import com.qoobot.qoostore.entity.License;
import com.qoobot.qoostore.service.CommerceService;
import com.qoobot.qoostore.service.LicenseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/commerce")
@RequiredArgsConstructor
@Tag(name = "商业化", description = "定价/订单/支付/License")
public class CommerceController {

    private final CommerceService commerceService;
    private final LicenseService licenseService;

    @PostMapping("/orders")
    @Operation(summary = "创建订单")
    public ApiResponse<OrderResponse> createOrder(
            @RequestParam UUID userId,
            @RequestParam String skillId,
            @RequestParam(defaultValue = "stripe") String paymentMethod) {
        return ApiResponse.success(commerceService.createOrder(userId, skillId, paymentMethod));
    }

    @GetMapping("/orders/{orderNo}")
    @Operation(summary = "订单详情")
    public ApiResponse<OrderResponse> getOrder(@PathVariable String orderNo) {
        return ApiResponse.success(commerceService.getOrder(orderNo));
    }

    @PostMapping("/orders/{orderNo}/pay")
    @Operation(summary = "支付回调")
    public ApiResponse<Void> processPayment(
            @PathVariable String orderNo,
            @RequestParam String paymentId) {
        commerceService.processPayment(orderNo, paymentId);
        return ApiResponse.success("Payment processed", null);
    }

    @GetMapping("/users/me/orders")
    @Operation(summary = "我的订单")
    public ApiResponse<Page<OrderResponse>> getUserOrders(
            @RequestParam UUID userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(commerceService.getUserOrders(userId, page, size));
    }

    @GetMapping("/users/me/licenses")
    @Operation(summary = "我的 License")
    public ApiResponse<List<License>> getUserLicenses(@RequestParam UUID userId) {
        return ApiResponse.success(licenseService.getUserLicenses(userId));
    }

    @PostMapping("/skills/{skillId}/reviews")
    @Operation(summary = "发表评价")
    public ApiResponse<Void> createReview(
            @RequestParam UUID userId,
            @PathVariable String skillId,
            @RequestParam Short rating,
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String content) {
        commerceService.createReview(userId, skillId, rating, title, content);
        return ApiResponse.success("Review created", null);
    }
}
