package com.qoobot.qoocommunity.governance.repository;

import com.qoobot.qoocommunity.governance.domain.RfcVote;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RfcVoteRepository extends JpaRepository<RfcVote, Long> {

    List<RfcVote> findByRfcId(Long rfcId);

    Optional<RfcVote> findByRfcIdAndUserId(Long rfcId, String userId);

    long countByRfcIdAndVote(Long rfcId, String vote);
}
