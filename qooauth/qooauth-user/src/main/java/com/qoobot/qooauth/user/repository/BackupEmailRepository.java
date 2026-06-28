package com.qoobot.qooauth.user.repository;

import com.qoobot.qooauth.user.entity.BackupEmailEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface BackupEmailRepository extends JpaRepository<BackupEmailEntity, Long> {
    List<BackupEmailEntity> findByUserId(String userId);
    List<BackupEmailEntity> findByUserIdAndVerifiedTrue(String userId);
    Optional<BackupEmailEntity> findByUserIdAndEmail(String userId, String email);
    boolean existsByUserIdAndEmail(String userId, String email);
}
