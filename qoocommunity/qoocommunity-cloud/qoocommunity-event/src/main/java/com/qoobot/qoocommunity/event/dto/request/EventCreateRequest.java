package com.qoobot.qoocommunity.event.dto.request;

import com.qoobot.qoocommunity.common.enums.EventType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class EventCreateRequest {

    @NotBlank
    private String title;

    @NotBlank
    private String slug;

    @NotNull
    private EventType type;

    private String description;
    private String contentHtml;
    private String coverUrl;
    private String location;

    @NotNull
    private LocalDateTime startTime;

    @NotNull
    private LocalDateTime endTime;

    private String timezone = "Asia/Shanghai";
    private Integer maxAttendees;
    private Boolean isFeatured = false;
}
