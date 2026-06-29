package com.qoobot.qoocommunity.forum.repository;

import com.qoobot.qoocommunity.forum.domain.Category;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CategoryRepository extends JpaRepository<Category, Long> {
    Optional<Category> findBySlug(String slug);
    List<Category> findByParentIdOrderBySortOrderAsc(Long parentId);
    List<Category> findByParentIdIsNullOrderBySortOrderAsc();
}
