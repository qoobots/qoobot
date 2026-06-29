package com.qoobot.qooauth.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AccessDecisionRepository extends JpaRepository<AccessDecisionEntity, Long> {
    List<AccessDecisionEntity> findByUserId(String userId);
    List<AccessDecisionEntity> findTop100ByUserIdOrderByDecidedAtDesc(String userId);
}
