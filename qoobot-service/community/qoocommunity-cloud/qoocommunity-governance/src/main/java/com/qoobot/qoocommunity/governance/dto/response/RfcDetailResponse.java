package com.qoobot.qoocommunity.governance.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class RfcDetailResponse {

    private Long id;
    private String title;
    private String number;
    private String status;
    private String content;
    private String contentHtml;
    private String authorId;
    private String authorName;
    private String sigName;
    private Integer voteYes;
    private Integer voteNo;
    private Integer voteAbstain;
    private String userVote;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
