package com.qoobot.qoocommunity.contributor.service;

import com.qoobot.qoocommunity.common.enums.ContributorLevel;
import com.qoobot.qoocommunity.contributor.domain.Contributor;
import com.qoobot.qoocommunity.contributor.repository.ContributorRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 贡献者等级自动评估服务。
 * 根据贡献数据自动推荐等级晋升。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LevelEvaluationService {

    private final ContributorRepository contributorRepository;

    /**
     * 评估单个贡献者等级
     */
    @Transactional
    public void evaluateLevel(String userId) {
        contributorRepository.findByUserId(userId).ifPresent(contributor -> {
            String newLevel = calculateLevel(contributor);
            if (!newLevel.equals(contributor.getLevel())) {
                String oldLevel = contributor.getLevel();
                contributor.setLevel(newLevel);
                contributor.setPromotedAt(LocalDateTime.now());
                contributorRepository.save(contributor);
                log.info("Contributor {} level changed: {} -> {}", userId, oldLevel, newLevel);
            }
        });
    }

    /**
     * 定时评估所有贡献者（每天凌晨2点）
     */
    @Scheduled(cron = "0 0 2 * * ?")
    @Transactional
    public void evaluateAllLevels() {
        log.info("Starting scheduled contributor level evaluation");
        List<Contributor> all = contributorRepository.findAll();
        for (Contributor c : all) {
            String newLevel = calculateLevel(c);
            if (!newLevel.equals(c.getLevel())) {
                c.setLevel(newLevel);
                c.setPromotedAt(LocalDateTime.now());
                contributorRepository.save(c);
            }
        }
        log.info("Completed contributor level evaluation for {} contributors", all.size());
    }

    /**
     * 根据贡献数据计算等级
     * CONTRIBUTOR: 至少签署 CLA，1+ PR
     * MAINTAINER: 10+ PR, 3+ 活跃月
     * COMMITTER: 20+ PR, 10+ Review, 6+ 活跃月
     */
    private String calculateLevel(Contributor c) {
        if (c.getPrCount() == null) c.setPrCount(0);
        if (c.getReviewCount() == null) c.setReviewCount(0);
        if (c.getActiveMonths() == null) c.setActiveMonths(0);

        if (c.getPrCount() >= 20 && c.getReviewCount() >= 10 && c.getActiveMonths() >= 6) {
            return ContributorLevel.COMMITTER.name();
        }
        if (c.getPrCount() >= 10 && c.getActiveMonths() >= 3) {
            return ContributorLevel.MAINTAINER.name();
        }
        if (c.getPrCount() >= 1 && Boolean.TRUE.equals(c.getClaSigned())) {
            return ContributorLevel.CONTRIBUTOR.name();
        }
        return c.getLevel() != null ? c.getLevel() : ContributorLevel.CONTRIBUTOR.name();
    }
}
