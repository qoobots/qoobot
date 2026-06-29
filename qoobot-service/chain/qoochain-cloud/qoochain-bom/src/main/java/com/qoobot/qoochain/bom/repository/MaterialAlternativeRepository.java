package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.MaterialAlternative;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface MaterialAlternativeRepository extends JpaRepository<MaterialAlternative, Long> {
    List<MaterialAlternative> findByMaterialId(Long materialId);
    List<MaterialAlternative> findByMaterialIdAndVerifiedTrue(Long materialId);
}
