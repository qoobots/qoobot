package com.qoobot.qoogear.developer.repository;

import com.qoobot.qoogear.developer.domain.ReferenceDesign;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ReferenceDesignRepository extends JpaRepository<ReferenceDesign, Long> {
    Page<ReferenceDesign> findByCategory(String category, Pageable pageable);
    Page<ReferenceDesign> findByTitleContainingIgnoreCase(String keyword, Pageable pageable);
}
