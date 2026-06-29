package com.qoobot.qoogear.standard.repository;

import com.qoobot.qoogear.standard.domain.TestChecklist;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface TestChecklistRepository extends JpaRepository<TestChecklist, Long> {
    List<TestChecklist> findByStandardId(Long standardId);
    List<TestChecklist> findByStandardIdAndRequiredTrue(Long standardId);
}
