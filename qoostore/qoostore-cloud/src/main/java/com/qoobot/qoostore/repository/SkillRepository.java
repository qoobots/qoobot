package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.Skill;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SkillRepository extends JpaRepository<Skill, Long> {
    Optional<Skill> findBySkillId(String skillId);
    Page<Skill> findByStatus(String status, Pageable pageable);
    Page<Skill> findByCategoryIdAndStatus(Long categoryId, String status, Pageable pageable);
    List<Skill> findByDeveloperId(Long developerId);

    @Query("SELECT s FROM Skill s WHERE s.status = 'published' AND " +
           "(LOWER(s.name) LIKE LOWER(CONCAT('%', :query, '%')) OR " +
           "LOWER(s.description) LIKE LOWER(CONCAT('%', :query, '%')))")
    Page<Skill> searchPublished(@Param("query") String query, Pageable pageable);

    @Query("SELECT s FROM Skill s WHERE s.status = 'published' AND s.pricingModel = :pricingModel")
    Page<Skill> findByPricingModel(@Param("pricingModel") String pricingModel, Pageable pageable);

    long countByDeveloperIdAndStatus(Long developerId, String status);
}
