package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.RecoveryCode;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RecoveryCodeRepository extends JpaRepository<RecoveryCode, Long> {

    Optional<RecoveryCode> findByUserIdAndCodeHashAndUsedFalse(String userId, String codeHash);

    List<RecoveryCode> findByUserIdAndUsedFalse(String userId);

    @Modifying
    @Query("DELETE FROM RecoveryCode r WHERE r.userId = :userId")
    void deleteByUserId(@Param("userId") String userId);

    long countByUserIdAndUsedFalse(String userId);
}
