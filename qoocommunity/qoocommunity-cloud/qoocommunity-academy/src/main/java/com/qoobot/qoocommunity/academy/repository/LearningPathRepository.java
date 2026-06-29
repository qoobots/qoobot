package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.LearningPath;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface LearningPathRepository extends JpaRepository<LearningPath, Long> {

    List<LearningPath> findByIsPublishedTrueOrderBySortOrderAsc();

    Optional<LearningPath> findBySlug(String slug);
}
