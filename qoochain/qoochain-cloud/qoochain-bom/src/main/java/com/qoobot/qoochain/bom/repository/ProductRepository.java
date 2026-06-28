package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    Optional<Product> findByModelCode(String modelCode);
    boolean existsByModelCode(String modelCode);
}
