package com.qoobot.qoocommunity.event.repository;

import com.qoobot.qoocommunity.event.domain.AgendaItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AgendaItemRepository extends JpaRepository<AgendaItem, Long> {
    List<AgendaItem> findByEventIdOrderBySortOrderAsc(Long eventId);
}
