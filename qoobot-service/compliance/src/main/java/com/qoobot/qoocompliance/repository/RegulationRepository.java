package com.qoobot.qoocompliance.repository;

import com.qoobot.qoocompliance.domain.Regulation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RegulationRepository extends JpaRepository<Regulation, Long> {

    Optional<Regulation> findByRegulationId(String regulationId);

    List<Regulation> findByMarket(String market);

    List<Regulation> findByCategory(String category);

    List<Regulation> findByStatus(String status);

    List<Regulation> findByMarketAndCategory(String market, String category);

    List<Regulation> findByMarketAndStatus(String market, String status);
}
