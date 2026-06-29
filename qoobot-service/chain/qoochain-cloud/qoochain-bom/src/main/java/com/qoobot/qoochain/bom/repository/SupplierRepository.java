package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.Supplier;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface SupplierRepository extends JpaRepository<Supplier, Long> {
    Optional<Supplier> findBySupplierCode(String supplierCode);
    List<Supplier> findByCategory(String category);
    List<Supplier> findByStatus(Supplier.SupplierStatus status);
    List<Supplier> findByRatingGreaterThanEqual(int minRating);
}
