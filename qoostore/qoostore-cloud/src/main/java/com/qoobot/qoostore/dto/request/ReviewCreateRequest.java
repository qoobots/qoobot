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
@Schema(description = "创建评价请求")
public class ReviewCreateRequest {

    @Min(value = 1, message = "评分最低为1星")
    @Max(value = 5, message = "评分最高为5星")
    @Schema(description = "评分 1-5星", example = "5", required = true)
    private Short rating;

    @Size(max = 255, message = "标题最长255个字符")
    @Schema(description = "评价标题", example = "非常棒的清洁技能")
    private String title;

    @Size(max = 5000, message = "评价内容最长5000个字符")
    @Schema(description = "评价内容", example = "这个技能让我的机器人清洁效率提升了3倍...")
    private String content;
}
