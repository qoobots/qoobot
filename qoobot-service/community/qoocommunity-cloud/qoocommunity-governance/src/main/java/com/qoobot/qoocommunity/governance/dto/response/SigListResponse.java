package com.qoobot.qoocommunity.governance.dto.response;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class SigListResponse {

    private Long id;
    private String name;
    private String slug;
    private String description;
    private String chairName;
    private Integer memberCount;
    private String meetingSchedule;
}
