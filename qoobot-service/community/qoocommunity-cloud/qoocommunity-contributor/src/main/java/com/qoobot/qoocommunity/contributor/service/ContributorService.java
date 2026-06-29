package com.qoobot.qoocommunity.contributor.service;

import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.contributor.domain.Contributor;
import com.qoobot.qoocommunity.contributor.repository.ContributorRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ContributorService {

    private final ContributorRepository contributorRepository;

    public Contributor getContributor(String userId) {
        return contributorRepository.findByUserId(userId)
                .orElseThrow(() -> QooCommunityException.notFound("Contributor not found: " + userId));
    }

    public List<Contributor> getTopContributors() {
        return contributorRepository.findAllByOrderByPrCountDesc();
    }

    @Transactional
    public Contributor signCla(String userId, String claType) {
        Contributor c = contributorRepository.findByUserId(userId)
                .orElseGet(() -> {
                    Contributor newC = new Contributor();
                    newC.setUserId(userId);
                    return newC;
                });
        c.setClaSigned(true);
        c.setClaSignedAt(LocalDateTime.now());
        c.setClaType(claType);
        c.setUpdatedAt(LocalDateTime.now());
        return contributorRepository.save(c);
    }

    @Transactional
    public void syncGithubContribution(String userId, int prCount, int commitCount, int reviewCount) {
        Contributor c = contributorRepository.findByUserId(userId)
                .orElseGet(() -> {
                    Contributor newC = new Contributor();
                    newC.setUserId(userId);
                    return newC;
                });
        c.setPrCount(c.getPrCount() + prCount);
        c.setCommitCount(c.getCommitCount() + commitCount);
        c.setReviewCount(c.getReviewCount() + reviewCount);
        c.setUpdatedAt(LocalDateTime.now());

        // Auto-evaluation for level promotion
        if (c.getPrCount() >= 10 && c.getClaSigned() && "CONTRIBUTOR".equals(c.getLevel())) {
            c.setLevel("MAINTAINER");
            c.setPromotedAt(LocalDateTime.now());
            log.info("User {} promoted to MAINTAINER", userId);
        }

        contributorRepository.save(c);
    }

    public long getContributorCount() {
        return contributorRepository.countByClaSignedTrue();
    }
}
