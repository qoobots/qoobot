package com.qoobot.qoocommunity.governance.repository;

import com.qoobot.qoocommunity.governance.domain.Sig;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SigRepository extends JpaRepository<Sig, Long> {
}
