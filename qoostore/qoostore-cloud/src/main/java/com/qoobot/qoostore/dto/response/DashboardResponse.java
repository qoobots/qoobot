package com.qoobot.qoostore.dto.response;

import lombok.*;
import java.math.BigDecimal;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DashboardResponse {
    private long totalSkills;
    private long totalDownloads;
    private BigDecimal totalRevenue;
    private long activeUsers;
    private Double avgRating;
    private Map<String, Long> downloadsByCategory;
    private Map<String, BigDecimal> revenueByMonth;
}
