package com.qoobot.qoogear.cert.repository;

import com.qoobot.qoogear.cert.domain.CertApplication;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CertApplicationRepository extends JpaRepository<CertApplication, Long> {
    Page<CertApplication> findByDeveloperId(Long developerId, Pageable pageable);
    Page<CertApplication> findByStatus(String status, Pageable pageable);
    List<CertApplication> findByAssignedLabId(Long labId);
    long countByStatus(String status);
    long countByDeveloperId(Long developerId);

    @Query("SELECT a FROM CertApplication a WHERE a.status IN :statuses")
    Page<CertApplication> findByStatusIn(@Param("statuses") List<String> statuses, Pageable pageable);
}
