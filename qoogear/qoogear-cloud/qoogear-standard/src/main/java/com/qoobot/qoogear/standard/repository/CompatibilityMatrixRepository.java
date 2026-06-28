package com.qoobot.qoogear.standard.repository;

import com.qoobot.qoogear.standard.domain.CompatibilityMatrix;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CompatibilityMatrixRepository extends JpaRepository<CompatibilityMatrix, Long> {
    List<CompatibilityMatrix> findBySpecIdA(Long specIdA);
    List<CompatibilityMatrix> findBySpecIdB(Long specIdB);
    List<CompatibilityMatrix> findByCompatibility(String compatibility);
}
