package com.qoobot.qoocommunity.event.dto.response;

import com.qoobot.qoocommunity.common.enums.EventStatus;
import com.qoobot.qoocommunity.common.enums.EventType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class EventListResponse {

    private Long id;
    private String title;
    private String slug;
    private EventType type;
    private String coverUrl;
    private String location;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private Integer currentAttendees;
    private EventStatus status;
    private Boolean isFeatured;
}
