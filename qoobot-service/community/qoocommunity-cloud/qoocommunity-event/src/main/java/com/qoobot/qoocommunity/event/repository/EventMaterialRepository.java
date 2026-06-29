package com.qoobot.qoocommunity.event.repository;

import com.qoobot.qoocommunity.event.domain.EventMaterial;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface EventMaterialRepository extends JpaRepository<EventMaterial, Long> {
    List<EventMaterial> findByEventId(Long eventId);
}
