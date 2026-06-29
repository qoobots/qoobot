package com.qoobot.qoocommunity.academy.dto.request;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ProgressUpdateRequest {

    @NotNull
    private Long lessonId;

    @NotNull
    @Min(0)
    @Max(100)
    private Integer progressPct;

    private Boolean isCompleted;
}
