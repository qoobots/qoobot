package com.qoobot.qooauth.developer.repository;

import com.qoobot.qooauth.developer.entity.DeveloperCertificate;
import com.qoobot.qooauth.developer.entity.SkillSignature;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DeveloperCertRepository extends JpaRepository<DeveloperCertificate, String> {

    List<DeveloperCertificate> findByUserId(String userId);

    List<DeveloperCertificate> findByState(String state);

    Optional<DeveloperCertificate> findBySerialNumber(String serialNumber);

    List<DeveloperCertificate> findByUserIdAndState(String userId, String state);

    @Query("SELECT c FROM DeveloperCertificate c WHERE c.teamId = :teamId AND c.state = 'ACTIVE'")
    List<DeveloperCertificate> findActiveByTeamId(@Param("teamId") String teamId);

    long countByUserIdAndCertTypeAndState(String userId, String certType, String state);
}

@Repository
interface SkillSignatureRepository extends JpaRepository<SkillSignature, String> {

    List<SkillSignature> findByDeveloperId(String developerId);

    Optional<SkillSignature> findBySkillHash(String skillHash);

    @Query("SELECT s FROM SkillSignature s WHERE s.developerId = :developerId AND s.verified = true")
    List<SkillSignature> findVerifiedByDeveloperId(@Param("developerId") String developerId);

    @Query("SELECT s FROM SkillSignature s WHERE s.skillHash = :skillHash AND s.verified = true")
    Optional<SkillSignature> findVerifiedBySkillHash(@Param("skillHash") String skillHash);
}
