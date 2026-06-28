package com.qoobot.qoostore.dto.response;

import lombok.*;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SkillListResponse {
    private List<SkillResponse> skills;
    private int page;
    private int size;
    private long totalElements;
    private int totalPages;
}
