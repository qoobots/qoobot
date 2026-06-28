package com.qoobot.qooauth.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RoleRepository extends JpaRepository<RoleEntity, Long> {
    Optional<RoleEntity> findByRoleId(String roleId);
    List<RoleEntity> findByCategory(String category);

    @Query("SELECT r FROM RoleEntity r WHERE r.roleId IN :roleIds")
    List<RoleEntity> findByRoleIds(@Param("roleIds") List<String> roleIds);
}
