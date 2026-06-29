package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.ComplianceItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ComplianceItemRepository extends JpaRepository<ComplianceItem, Long> {

    Optional<ComplianceItem> findByItemId(String itemId);

    List<ComplianceItem> findByChecklistId(String checklistId);

    List<ComplianceItem> findByProjectId(String projectId);

    List<ComplianceItem> findByCategory(String category);

    List<ComplianceItem> findByStatus(String status);

    List<ComplianceItem> findByPriority(String priority);

    List<ComplianceItem> findByChecklistIdAndCategory(String checklistId, String category);

    List<ComplianceItem> findByChecklistIdAndStatus(String checklistId, String status);

    List<ComplianceItem> findByChecklistIdAndCategoryAndStatus(String checklistId, String category, String status);
}
