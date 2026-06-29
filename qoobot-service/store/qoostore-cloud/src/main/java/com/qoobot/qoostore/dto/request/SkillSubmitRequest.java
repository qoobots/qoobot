package com.qoobot.qoostore.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "技能提交请求")
public class SkillSubmitRequest {

    @NotBlank(message = "技能ID不能为空")
    @Schema(description = "技能唯一标识 (反向域名)", example = "com.example.cleaning", required = true)
    private String skillId;

    @NotBlank(message = "技能名称不能为空")
    @Size(max = 128, message = "技能名称最长128个字符")
    @Schema(description = "技能名称", example = "智能清洁助手", required = true)
    private String name;

    @Size(max = 5000, message = "技能描述最长5000个字符")
    @Schema(description = "技能描述", example = "AI驱动的全屋清洁技能，支持多种地面材质识别")
    private String description;

    @NotNull(message = "分类ID不能为空")
    @Schema(description = "分类ID", required = true)
    private Long categoryId;

    @Size(max = 255, message = "一句话简介最长255个字符")
    @Schema(description = "一句话简介", example = "让你的机器人成为清洁专家")
    private String tagline;

    @Schema(description = "定价模型", example = "free", allowableValues = {"free", "paid", "subscription", "usage"})
    private String pricingModel;

    @Schema(description = "图标URL")
    private String iconUrl;

    @Schema(description = "截图URL列表")
    private java.util.List<String> screenshotUrls;

    @Schema(description = "演示视频URL")
    private String videoUrl;

    @Schema(description = "支持的机器人型号列表", example = "[\"QS\", \"QL\", \"QP\"]")
    private java.util.List<String> supportedModels;

    @Schema(description = "最低QOS版本", example = "2.0.0")
    private String minQosVersion;

    @Schema(description = "技能标签", example = "[\"ai\", \"cleaning\", \"home\"]")
    private java.util.List<String> tags;

    @Schema(description = "隐私标签等级", example = "low", allowableValues = {"low", "medium", "high"})
    private String privacyLevel;

    @Schema(description = "manifest.json 内容 (JSON字符串)")
    private String manifestJson;
}
