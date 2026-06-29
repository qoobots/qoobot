package com.qoobot.qoogear.cert.repository;

import com.qoobot.qoogear.cert.domain.Developer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface DeveloperRepository extends JpaRepository<Developer, Long> {
    Optional<Developer> findByUserId(Long userId);
    boolean existsByUserId(Long userId);
    boolean existsByContactEmail(String email);
}
