package com.qoobot.qoostore.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "提现/结算请求")
public class PayoutRequest {

    @NotBlank(message = "结算方式不能为空")
    @Schema(description = "结算方式", example = "stripe", allowableValues = {"stripe", "alipay", "bank_transfer"}, required = true)
    private String payoutMethod;

    @Schema(description = "结算金额（默认结算全部可用余额）", example = "1000.00")
    private java.math.BigDecimal amount;

    @Schema(description = "币种", example = "USD")
    private String currency;

    @Schema(description = "结算周期开始日期", example = "2026-06-01")
    private String periodStart;

    @Schema(description = "结算周期结束日期", example = "2026-06-30")
    private String periodEnd;
}
