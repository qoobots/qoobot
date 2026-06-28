package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.CostRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface CostRecordRepository extends JpaRepository<CostRecord, Long> {
    List<CostRecord> findByMaterialIdOrderByEffectiveFromDesc(Long materialId);
    Optional<CostRecord> findByMaterialIdAndSupplierIdAndEffectiveToIsNull(Long materialId, Long supplierId);
    List<CostRecord> findByEffectiveFromBetween(LocalDate from, LocalDate to);
}
