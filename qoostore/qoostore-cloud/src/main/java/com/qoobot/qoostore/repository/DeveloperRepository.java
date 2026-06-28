package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.Developer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface DeveloperRepository extends JpaRepository<Developer, Long> {
    Optional<Developer> findByUserId(UUID userId);
    Optional<Developer> findByUsername(String username);
    Optional<Developer> findByEmail(String email);
    boolean existsByUsername(String username);
    boolean existsByEmail(String email);
}
