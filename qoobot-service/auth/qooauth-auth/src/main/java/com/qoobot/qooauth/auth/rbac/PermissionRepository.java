package com.qoobot.qooauth.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PermissionRepository extends JpaRepository<PermissionEntity, Long> {
    Optional<PermissionEntity> findByPermissionId(String permissionId);
    List<PermissionEntity> findByResourceType(String resourceType);

    @Query("SELECT p FROM PermissionEntity p WHERE p.resourceType = :resourceType AND p.action = :action")
    Optional<PermissionEntity> findByResourceAndAction(@Param("resourceType") String resourceType,
                                                        @Param("action") String action);

    @Query("SELECT p FROM PermissionEntity p WHERE p.permissionId IN :permissionIds")
    List<PermissionEntity> findByPermissionIds(@Param("permissionIds") List<String> permissionIds);
}
