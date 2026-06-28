package com.qoobot.qoocommunity.academy.repository;

import com.qoobot.qoocommunity.academy.domain.Certification;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface CertificationRepository extends JpaRepository<Certification, Long> {
    List<Certification> findByIsActiveTrue();
    List<Certification> findByLevel(String level);
}
