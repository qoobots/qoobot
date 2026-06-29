package com.qoobot.qoostore.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "技能搜索请求")
public class SkillSearchRequest {

    @Schema(description = "搜索关键词", example = "清洁")
    @Size(max = 200, message = "搜索关键词最长200个字符")
    private String query;

    @Schema(description = "分类slug", example = "home")
    private String categorySlug;

    @Schema(description = "排序方式", example = "newest", allowableValues = {"newest", "rating", "downloads", "price_asc", "price_desc"})
    private String sortBy;

    @Schema(description = "定价模型过滤", example = "free", allowableValues = {"free", "paid", "subscription", "all"})
    private String pricingModel;

    @Schema(description = "最低评分过滤", example = "4.0")
    @Min(0) @Max(5)
    private Double minRating;

    @Schema(description = "页码", example = "0")
    @Min(0)
    private Integer page;

    @Schema(description = "每页大小", example = "20")
    @Min(1) @Max(100)
    private Integer size;

    @Schema(description = "支持的机器人型号", example = "QS")
    private String robotModel;

    @Schema(description = "最低QOS版本", example = "2.0.0")
    private String minQosVersion;

    @Schema(description = "标签过滤", example = "ai,cleaning")
    private String tags;
}
