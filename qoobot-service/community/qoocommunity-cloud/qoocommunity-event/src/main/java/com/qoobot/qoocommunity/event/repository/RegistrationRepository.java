package com.qoobot.qoocommunity.event.repository;

import com.qoobot.qoocommunity.event.domain.Registration;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface RegistrationRepository extends JpaRepository<Registration, Long> {
    List<Registration> findByEventId(Long eventId);
    Optional<Registration> findByEventIdAndUserId(Long eventId, String userId);
    long countByEventId(Long eventId);
    List<Registration> findByUserIdOrderByCreatedAtDesc(String userId);
}
