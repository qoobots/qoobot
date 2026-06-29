package com.qoobot.qoocommunity.governance.dto.response;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class RoadmapResponse {

    private String quarter;
    private String title;
    private String description;
    private String status;
    private Integer completedItems;
    private Integer totalItems;
}
