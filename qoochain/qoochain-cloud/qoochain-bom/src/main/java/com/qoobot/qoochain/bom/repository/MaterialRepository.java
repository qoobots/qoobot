package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.Material;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface MaterialRepository extends JpaRepository<Material, Long> {
    Optional<Material> findByMaterialCode(String materialCode);
    List<Material> findByCategory(String category);
    List<Material> findByLifecycle(Material.Lifecycle lifecycle);
    boolean existsByMaterialCode(String materialCode);
}
