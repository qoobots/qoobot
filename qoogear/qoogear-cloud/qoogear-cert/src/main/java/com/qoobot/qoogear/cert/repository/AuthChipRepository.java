package com.qoobot.qoogear.cert.repository;

import com.qoobot.qoogear.cert.domain.AuthChip;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface AuthChipRepository extends JpaRepository<AuthChip, Long> {
    Optional<AuthChip> findByChipId(String chipId);
    List<AuthChip> findByCertificateId(Long certificateId);
    List<AuthChip> findByBatchNumber(String batchNumber);
    long countByCertificateIdAndStatus(Long certificateId, String status);
}
