package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.RobotTrustGroup;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RobotTrustGroupRepository extends JpaRepository<RobotTrustGroup, String> {

    List<RobotTrustGroup> findByOwnerUserId(String ownerUserId);

    List<RobotTrustGroup> findByOwnerUserIdAndState(String ownerUserId, String state);

    Optional<RobotTrustGroup> findByGroupIdAndState(String groupId, String state);

    @Query("SELECT g FROM RobotTrustGroup g WHERE g.state = 'ACTIVE'")
    List<RobotTrustGroup> findAllActive();

    @Modifying
    @Query("UPDATE RobotTrustGroup g SET g.state = :state, g.dissolvedAt = CURRENT_TIMESTAMP WHERE g.groupId = :groupId")
    void dissolveGroup(@Param("groupId") String groupId, @Param("state") String state);
}
