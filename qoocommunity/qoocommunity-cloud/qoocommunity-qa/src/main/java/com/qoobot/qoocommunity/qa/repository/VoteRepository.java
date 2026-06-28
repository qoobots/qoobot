package com.qoobot.qoocommunity.qa.repository;

import com.qoobot.qoocommunity.qa.domain.Vote;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface VoteRepository extends JpaRepository<Vote, Long> {
    Optional<Vote> findByUserIdAndTargetTypeAndTargetId(String userId, String targetType, Long targetId);
    long countByTargetTypeAndTargetIdAndVoteType(String targetType, Long targetId, String voteType);
}
