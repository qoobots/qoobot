package com.qoobot.qooauth.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface UserRoleRepository extends JpaRepository<UserRoleEntity, Long> {

    @Query("SELECT ur FROM UserRoleEntity ur WHERE ur.userId = :userId " +
           "AND (ur.expiresAt IS NULL OR ur.expiresAt > :now)")
    List<UserRoleEntity> findActiveByUserId(@Param("userId") String userId, @Param("now") Instant now);

    List<UserRoleEntity> findByUserId(String userId);

    boolean existsByUserIdAndRoleId(String userId, String roleId);
}
