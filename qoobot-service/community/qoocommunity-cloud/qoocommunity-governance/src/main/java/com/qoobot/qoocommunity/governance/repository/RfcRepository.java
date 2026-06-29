package com.qoobot.qoocommunity.governance.repository;

import com.qoobot.qoocommunity.governance.domain.Rfc;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface RfcRepository extends JpaRepository<Rfc, Long> {
    List<Rfc> findByStatusOrderByCreatedAtDesc(String status);
    List<Rfc> findAllByOrderByCreatedAtDesc();
}
