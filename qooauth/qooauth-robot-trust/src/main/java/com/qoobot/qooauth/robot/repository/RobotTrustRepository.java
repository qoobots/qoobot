package com.qoobot.qooauth.robot.repository;

import com.qoobot.qooauth.robot.entity.CollaborationToken;
import com.qoobot.qooauth.robot.entity.RobotTrustGroup;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface RobotTrustRepository extends JpaRepository<RobotTrustGroup, String> {

    List<RobotTrustGroup> findByOwnerDeviceId(String ownerDeviceId);

    List<RobotTrustGroup> findByState(String state);

    @Query("SELECT g FROM RobotTrustGroup g WHERE g.ownerDeviceId = :deviceId AND g.state = 'ACTIVE'")
    List<RobotTrustGroup> findActiveGroupsByDeviceId(@Param("deviceId") String deviceId);
}

@Repository
interface CollaborationTokenRepository extends JpaRepository<CollaborationToken, String> {

    List<CollaborationToken> findByIssuerDeviceId(String issuerDeviceId);

    List<CollaborationToken> findByRecipientDeviceId(String recipientDeviceId);

    List<CollaborationToken> findByState(String state);

    @Query("SELECT t FROM CollaborationToken t WHERE (t.issuerDeviceId = :deviceId OR t.recipientDeviceId = :deviceId) AND t.state = 'ACTIVE' AND t.expiresAt > :now")
    List<CollaborationToken> findActiveTokensForDevice(@Param("deviceId") String deviceId, @Param("now") Instant now);

    @Query("SELECT t FROM CollaborationToken t WHERE t.state = 'ACTIVE' AND t.expiresAt <= :now")
    List<CollaborationToken> findExpiredActiveTokens(@Param("now") Instant now);
}
