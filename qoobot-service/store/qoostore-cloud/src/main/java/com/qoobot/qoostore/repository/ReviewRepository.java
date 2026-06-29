package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.Review;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.math.BigDecimal;
import java.util.UUID;

@Repository
public interface ReviewRepository extends JpaRepository<Review, Long> {
    Page<Review> findBySkillIdAndStatusOrderByCreatedAtDesc(Long skillId, String status, Pageable pageable);
    Page<Review> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
    boolean existsBySkillIdAndUserId(Long skillId, UUID userId);

    @Query("SELECT COALESCE(AVG(r.rating), 0) FROM Review r WHERE r.skillId = :skillId AND r.status = 'published'")
    BigDecimal getAverageRating(@Param("skillId") Long skillId);

    @Query("SELECT COUNT(r) FROM Review r WHERE r.skillId = :skillId AND r.status = 'published'")
    long countBySkillId(@Param("skillId") Long skillId);
}
