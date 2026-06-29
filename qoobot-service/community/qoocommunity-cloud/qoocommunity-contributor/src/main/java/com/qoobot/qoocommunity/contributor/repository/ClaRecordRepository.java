package com.qoobot.qoocommunity.contributor.repository;

import com.qoobot.qoocommunity.contributor.domain.ClaRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface ClaRecordRepository extends JpaRepository<ClaRecord, Long> {

    Optional<ClaRecord> findTopByUserIdOrderBySignedAtDesc(String userId);

    boolean existsByUserId(String userId);
}
