package com.qoobot.qoogear.standard.repository;

import com.qoobot.qoogear.standard.domain.StandardSpec;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface StandardSpecRepository extends JpaRepository<StandardSpec, Long> {
    Page<StandardSpec> findByCategoryId(Long categoryId, Pageable pageable);
    Page<StandardSpec> findByStatus(String status, Pageable pageable);
    Optional<StandardSpec> findBySpecNumberAndVersion(String specNumber, String version);
    List<StandardSpec> findBySpecNumberOrderByVersionDesc(String specNumber);

    @Query("SELECT s FROM StandardSpec s WHERE LOWER(s.title) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    Page<StandardSpec> searchByTitle(@Param("keyword") String keyword, Pageable pageable);

    long countByStatus(String status);
}
