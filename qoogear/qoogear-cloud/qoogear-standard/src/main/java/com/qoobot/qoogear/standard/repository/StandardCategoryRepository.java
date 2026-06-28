package com.qoobot.qoogear.standard.repository;

import com.qoobot.qoogear.standard.domain.StandardCategory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface StandardCategoryRepository extends JpaRepository<StandardCategory, Long> {
    Optional<StandardCategory> findBySlug(String slug);
    List<StandardCategory> findByParentId(Long parentId);
    List<StandardCategory> findByParentIdIsNull();
}
