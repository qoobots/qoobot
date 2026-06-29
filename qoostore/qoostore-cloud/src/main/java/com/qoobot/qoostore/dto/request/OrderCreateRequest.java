package com.qoobot.qoostore.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "创建订单请求")
public class OrderCreateRequest {

    @NotBlank(message = "技能ID不能为空")
    @Schema(description = "技能ID", example = "com.example.cleaning", required = true)
    private String skillId;

    @Schema(description = "版本号（默认最新版本）", example = "1.2.3")
    private String version;

    @Schema(description = "优惠券码")
    private String couponCode;

    @Schema(description = "支付方式", example = "stripe", allowableValues = {"stripe", "alipay", "wechat", "apple_pay", "google_pay"})
    private String paymentMethod;

    @Schema(description = "目标机器人设备ID", example = "QBS-2024-00001")
    private String deviceId;

    @Schema(description = "币种", example = "USD")
    private String currency;
}
