package com.qoobot.qoocommunity.governance.dto.response;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class TscListResponse {

    private Long id;
    private String userId;
    private String nickname;
    private String avatarUrl;
    private String role;
    private String termStart;
    private String termEnd;
    private Boolean isActive;
}
