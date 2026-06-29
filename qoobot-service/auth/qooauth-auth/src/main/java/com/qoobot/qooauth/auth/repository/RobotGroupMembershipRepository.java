package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.RobotGroupMembership;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RobotGroupMembershipRepository extends JpaRepository<RobotGroupMembership, String> {

    List<RobotGroupMembership> findByGroupId(String groupId);

    List<RobotGroupMembership> findByGroupIdAndState(String groupId, String state);

    List<RobotGroupMembership> findByDeviceIdAndState(String deviceId, String state);

    Optional<RobotGroupMembership> findByGroupIdAndDeviceId(String groupId, String deviceId);

    @Query("SELECT m FROM RobotGroupMembership m WHERE m.groupId = :groupId AND m.state = 'ACTIVE'")
    List<RobotGroupMembership> findActiveMembersByGroup(@Param("groupId") String groupId);

    @Query("SELECT m FROM RobotGroupMembership m WHERE m.deviceId = :deviceId AND m.state = 'ACTIVE'")
    List<RobotGroupMembership> findActiveGroupsForDevice(@Param("deviceId") String deviceId);

    @Query("SELECT COUNT(m) FROM RobotGroupMembership m WHERE m.groupId = :groupId AND m.state = 'ACTIVE'")
    long countActiveMembers(@Param("groupId") String groupId);

    @Modifying
    @Query("UPDATE RobotGroupMembership m SET m.state = :state, m.leftAt = CURRENT_TIMESTAMP WHERE m.membershipId = :membershipId")
    void updateMembershipState(@Param("membershipId") String membershipId, @Param("state") String state);
}
