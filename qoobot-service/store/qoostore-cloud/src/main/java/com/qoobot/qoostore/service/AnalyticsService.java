package com.qoobot.qoostore.service;

import com.qoobot.qoostore.dto.response.DashboardResponse;
import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnalyticsService {

    private final SkillRepository skillRepository;
    private final SkillStatsRepository statsRepository;
    private final ReviewRepository reviewRepository;
    private final DeveloperRevenueRepository revenueRepository;
    private final OrderRepository orderRepository;

    public DashboardResponse getPlatformOverview() {
        long totalSkills = skillRepository.count();
        LocalDate today = LocalDate.now();

        List<SkillStats> todayStats = statsRepository.findTopDownloadedByDate(today,
                org.springframework.data.domain.PageRequest.of(0, 1000));

        long totalDownloads = todayStats.stream().mapToLong(SkillStats::getDownloads).sum();
        BigDecimal totalRevenue = todayStats.stream()
                .map(SkillStats::getRevenue)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        long activeUsers = todayStats.stream().mapToLong(SkillStats::getActiveUsers).sum();

        Map<String, Long> downloadsByCategory = new HashMap<>();
        Map<String, BigDecimal> revenueByMonth = new HashMap<>();

        return DashboardResponse.builder()
                .totalSkills(totalSkills)
                .totalDownloads(totalDownloads)
                .totalRevenue(totalRevenue)
                .activeUsers(activeUsers)
                .avgRating(4.5)
                .downloadsByCategory(downloadsByCategory)
                .revenueByMonth(revenueByMonth)
                .build();
    }

    public BigDecimal getDeveloperRevenue(Long developerId, LocalDate startDate, LocalDate endDate) {
        return revenueRepository.findByDeveloperIdAndCreatedAtBetween(developerId,
                startDate.atStartOfDay(), endDate.plusDays(1).atStartOfDay())
                .stream()
                .map(DeveloperRevenue::getDeveloperShare)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    public Map<String, Object> getDeveloperDashboard(Long developerId) {
        List<Skill> skills = skillRepository.findByDeveloperId(developerId);
        long totalDownloads = 0;
        BigDecimal totalRevenue = BigDecimal.ZERO;

        for (Skill skill : skills) {
            List<SkillStats> stats = statsRepository.findBySkillIdAndDateBetweenOrderByDateAsc(
                    skill.getId(), LocalDate.now().minusDays(30), LocalDate.now());
            totalDownloads += stats.stream().mapToLong(SkillStats::getDownloads).sum();
            totalRevenue = totalRevenue.add(stats.stream()
                    .map(SkillStats::getRevenue)
                    .reduce(BigDecimal.ZERO, BigDecimal::add));
        }

        Map<String, Object> dashboard = new HashMap<>();
        dashboard.put("totalSkills", skills.size());
        dashboard.put("publishedSkills", skills.stream().filter(s -> "published".equals(s.getStatus())).count());
        dashboard.put("totalDownloads", totalDownloads);
        dashboard.put("totalRevenue", totalRevenue);
        dashboard.put("avgRating", 4.0);
        return dashboard;
    }
}
