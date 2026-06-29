package com.qoobot.qoocommunity.contributor.repository;

import com.qoobot.qoocommunity.contributor.domain.Contributor;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ContributorRepository extends JpaRepository<Contributor, Long> {
    Optional<Contributor> findByUserId(String userId);
    List<Contributor> findByLevelOrderByPrCountDesc(String level);
    List<Contributor> findAllByOrderByPrCountDesc();
    long countByClaSignedTrue();
}
