package com.qoobot.qoogear.lab.repository;

import com.qoobot.qoogear.lab.domain.Laboratory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

@Repository
public interface LaboratoryRepository extends JpaRepository<Laboratory, Long> {
    Optional<Laboratory> findByLabCode(String labCode);
    List<Laboratory> findByStatus(String status);
    List<Laboratory> findByCountry(String country);
}
