package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.Bom;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface BomRepository extends JpaRepository<Bom, Long> {
    List<Bom> findByProductId(Long productId);
    Optional<Bom> findByProductIdAndVersionAndBomType(Long productId, String version, Bom.BomType bomType);
    List<Bom> findByStatus(Bom.BomStatus status);
}
