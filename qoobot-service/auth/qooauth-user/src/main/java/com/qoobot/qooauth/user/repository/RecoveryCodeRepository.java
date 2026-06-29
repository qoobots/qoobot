package com.qoobot.qooauth.user.repository;

import com.qoobot.qooauth.user.entity.RecoveryCodeEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RecoveryCodeRepository extends JpaRepository<RecoveryCodeEntity, Long> {
    List<RecoveryCodeEntity> findByUserIdAndUsedFalse(String userId);
    long countByUserIdAndUsedFalse(String userId);
}
