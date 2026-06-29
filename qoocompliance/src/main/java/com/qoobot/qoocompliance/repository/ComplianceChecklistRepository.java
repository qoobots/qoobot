package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.ComplianceChecklist;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ComplianceChecklistRepository extends JpaRepository<ComplianceChecklist, Long> {

    Optional<ComplianceChecklist> findByChecklistId(String checklistId);

    List<ComplianceChecklist> findByProjectId(String projectId);

    List<ComplianceChecklist> findByMarket(String market);

    List<ComplianceChecklist> findByStatus(String status);

    List<ComplianceChecklist> findByProjectIdAndMarket(String projectId, String market);
}
