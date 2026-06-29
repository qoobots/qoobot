package com.qoobot.qoochain.bom.repository;

import com.qoobot.qoochain.bom.domain.BomItem;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface BomItemRepository extends JpaRepository<BomItem, Long> {
    List<BomItem> findByBomIdOrderBySortOrder(Long bomId);
    List<BomItem> findByBomIdAndParentItemId(Long bomId, Long parentItemId);
    List<BomItem> findByBomIdAndParentItemIsNullOrderBySortOrder(Long bomId);
    void deleteByBomId(Long bomId);
}
