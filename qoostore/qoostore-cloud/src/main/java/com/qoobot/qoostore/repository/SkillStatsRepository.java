package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.SkillStats;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface SkillStatsRepository extends JpaRepository<SkillStats, Long> {
    Optional<SkillStats> findBySkillIdAndDate(Long skillId, LocalDate date);
    List<SkillStats> findBySkillIdAndDateBetweenOrderByDateAsc(Long skillId, LocalDate start, LocalDate end);

    @Query("SELECT s FROM SkillStats s WHERE s.date = :date ORDER BY s.downloads DESC")
    List<SkillStats> findTopDownloadedByDate(@Param("date") LocalDate date, org.springframework.data.domain.Pageable pageable);

    @Query("SELECT s FROM SkillStats s WHERE s.date = :date ORDER BY s.revenue DESC")
    List<SkillStats> findTopGrossingByDate(@Param("date") LocalDate date, org.springframework.data.domain.Pageable pageable);
}
