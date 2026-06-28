package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.SkillVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SkillVersionRepository extends JpaRepository<SkillVersion, Long> {
    List<SkillVersion> findBySkillIdOrderByCreatedAtDesc(Long skillId);
    Optional<SkillVersion> findBySkillIdAndVersion(Long skillId, String version);
    Optional<SkillVersion> findBySkillIdAndStatus(Long skillId, String status);
    long countBySkillId(Long skillId);
}
