package com.qoobot.qooauth.user.repository;

import com.qoobot.qooauth.user.entity.RecoverySessionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RecoverySessionRepository extends JpaRepository<RecoverySessionEntity, Long> {
    Optional<RecoverySessionEntity> findBySessionToken(String sessionToken);
}
