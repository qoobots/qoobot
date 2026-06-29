package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.RegulationChange;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RegulationChangeRepository extends JpaRepository<RegulationChange, Long> {

    List<RegulationChange> findByRegulationId(String regulationId);

    List<RegulationChange> findByChangeType(String changeType);

    List<RegulationChange> findByImpactLevel(String impactLevel);

    List<RegulationChange> findByNotified(Boolean notified);

    List<RegulationChange> findByRegulationIdAndChangeType(String regulationId, String changeType);
}
