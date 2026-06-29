package com.qoobot.qoocommunity.academy.dto.response;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class CertResultResponse {

    private Long certificationId;
    private String certificationName;
    private String level;
    private Integer score;
    private Boolean passed;
    private String certificateUrl;
    private LocalDateTime issuedAt;
    private LocalDateTime expiresAt;
}
