package com.qoobot.qooauth.auth.repository;

import com.qoobot.qooauth.auth.entity.SkillSignature;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface SkillSignatureRepository extends JpaRepository<SkillSignature, String> {

    List<SkillSignature> findBySkillId(String skillId);

    List<SkillSignature> findBySkillIdAndState(String skillId, String state);

    Optional<SkillSignature> findBySkillIdAndSkillVersion(String skillId, String skillVersion);

    List<SkillSignature> findByDeveloperUserId(String developerUserId);

    List<SkillSignature> findByDeveloperCertId(String developerCertId);

    @Modifying
    @Query("UPDATE SkillSignature s SET s.state = 'REVOKED' WHERE s.developerCertId = :certId AND s.state = 'VALID'")
    int revokeByCertificateId(@Param("certId") String certId);

    @Query("SELECT s FROM SkillSignature s WHERE s.skillId = :skillId ORDER BY s.signedAt DESC")
    List<SkillSignature> findVersionHistory(@Param("skillId") String skillId);
}
