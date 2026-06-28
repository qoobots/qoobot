package com.qoobot.qoocommunity.content.repository;

import com.qoobot.qoocommunity.content.domain.Showcase;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ShowcaseRepository extends JpaRepository<Showcase, Long> {
    Page<Showcase> findByStatusOrderByCreatedAtDesc(String status, Pageable pageable);
    Page<Showcase> findByIsFeaturedTrueAndStatusOrderByCreatedAtDesc(String status, Pageable pageable);
}
