package com.qoobot.qoostore.dto.response;

import lombok.*;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReviewResponse {
    private Long id;
    private Long skillId;
    private String userName;
    private Short rating;
    private String title;
    private String content;
    private Integer helpfulCount;
    private LocalDateTime createdAt;
}
