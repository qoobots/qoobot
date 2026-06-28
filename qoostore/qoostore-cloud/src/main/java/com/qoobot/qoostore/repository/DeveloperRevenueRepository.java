package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.DeveloperRevenue;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface DeveloperRevenueRepository extends JpaRepository<DeveloperRevenue, Long> {
    List<DeveloperRevenue> findByDeveloperIdAndCreatedAtBetween(
            Long developerId, LocalDateTime start, LocalDateTime end);

    @Query("SELECT COALESCE(SUM(dr.developerShare), 0) FROM DeveloperRevenue dr WHERE dr.developerId = :developerId")
    BigDecimal sumDeveloperShareByDeveloperId(@Param("developerId") Long developerId);
}
