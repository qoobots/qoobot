package com.qoobot.qoogear.cert.repository;

import com.qoobot.qoogear.cert.domain.TestReport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TestReportRepository extends JpaRepository<TestReport, Long> {
    List<TestReport> findByApplicationId(Long applicationId);
    List<TestReport> findByLaboratoryId(Long laboratoryId);
    long countByApplicationId(Long applicationId);
}
