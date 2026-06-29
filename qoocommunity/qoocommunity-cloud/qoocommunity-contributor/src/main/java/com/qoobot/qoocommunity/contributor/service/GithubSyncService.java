package com.qoobot.qoocommunity.contributor.service;

import com.qoobot.qoocommunity.contributor.domain.Contributor;
import com.qoobot.qoocommunity.contributor.repository.ContributorRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * GitHub 数据同步服务。
 * 通过 GitHub API / Webhook 同步贡献者数据。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GithubSyncService {

    private final ContributorRepository contributorRepository;

    /**
     * 处理 GitHub PR 合并事件
     */
    @Transactional
    public void onPullRequestMerged(String userId) {
        contributorRepository.findByUserId(userId).ifPresentOrElse(
                contributor -> {
                    contributor.setPrCount(contributor.getPrCount() != null ? contributor.getPrCount() + 1 : 1);
                    contributorRepository.save(contributor);
                    log.info("PR merged for contributor: {}, total PRs: {}", userId, contributor.getPrCount());
                },
                () -> {
                    // 新贡献者自动创建记录
                    Contributor newContributor = new Contributor();
                    newContributor.setUserId(userId);
                    newContributor.setPrCount(1);
                    newContributor.setLevel("CONTRIBUTOR");
                    contributorRepository.save(newContributor);
                    log.info("New contributor created: {}", userId);
                }
        );
    }

    /**
     * 处理 GitHub Code Review 事件
     */
    @Transactional
    public void onReviewSubmitted(String userId) {
        contributorRepository.findByUserId(userId).ifPresent(contributor -> {
            contributor.setReviewCount(contributor.getReviewCount() != null ? contributor.getReviewCount() + 1 : 1);
            contributorRepository.save(contributor);
        });
    }

    /**
     * 更新活跃月份数
     */
    @Transactional
    public void updateActiveMonths(String userId, int months) {
        contributorRepository.findByUserId(userId).ifPresent(contributor -> {
            contributor.setActiveMonths(months);
            contributorRepository.save(contributor);
        });
    }
}
