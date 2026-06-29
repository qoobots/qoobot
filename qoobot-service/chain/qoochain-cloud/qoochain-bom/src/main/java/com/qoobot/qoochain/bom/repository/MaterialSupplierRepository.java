package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.MaterialSupplier;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface MaterialSupplierRepository extends JpaRepository<MaterialSupplier, Long> {
    List<MaterialSupplier> findByMaterialId(Long materialId);
    List<MaterialSupplier> findBySupplierId(Long supplierId);
    Optional<MaterialSupplier> findByMaterialIdAndSupplierId(Long materialId, Long supplierId);
    List<MaterialSupplier> findByMaterialIdAndIsPreferredTrue(Long materialId);
}
