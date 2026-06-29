package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.DeveloperPayout;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface DeveloperPayoutRepository extends JpaRepository<DeveloperPayout, Long> {
    List<DeveloperPayout> findByDeveloperIdOrderByCreatedAtDesc(Long developerId);
}
