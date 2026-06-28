package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.AnomalyEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface AnomalyEventRepository extends JpaRepository<AnomalyEvent, String> {

    List<AnomalyEvent> findByUserIdAndCreatedAtAfter(String userId, Instant after);

    List<AnomalyEvent> findByIpAddressAndCreatedAtAfter(String ipAddress, Instant after);

    List<AnomalyEvent> findByRiskLevelAndResolved(String riskLevel, boolean resolved);

    @Query("SELECT a FROM AnomalyEvent a WHERE a.userId = :userId AND a.createdAt > :since ORDER BY a.createdAt DESC")
    List<AnomalyEvent> findRecentByUserId(@Param("userId") String userId, @Param("since") Instant since);

    @Query("SELECT COUNT(a) FROM AnomalyEvent a WHERE a.ipAddress = :ip AND a.eventType = :eventType AND a.createdAt > :since")
    long countByIpAndTypeSince(@Param("ip") String ip, @Param("eventType") String eventType, @Param("since") Instant since);

    long countByUserIdAndRiskLevelAndCreatedAtAfter(String userId, String riskLevel, Instant after);

    @Query("SELECT a.ipAddress, COUNT(a) as cnt FROM AnomalyEvent a WHERE a.createdAt > :since GROUP BY a.ipAddress ORDER BY cnt DESC")
    List<Object[]> findTopOffendingIps(@Param("since") Instant since);
}
