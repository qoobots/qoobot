package com.qoobot.qoocommunity.event.repository;

import com.qoobot.qoocommunity.event.domain.Event;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;

public interface EventRepository extends JpaRepository<Event, Long> {

    Page<Event> findByStatusOrderByStartTimeAsc(String status, Pageable pageable);

    List<Event> findByStartTimeAfterAndStatusOrderByStartTimeAsc(LocalDateTime after, String status);

    Page<Event> findByTypeOrderByStartTimeDesc(String type, Pageable pageable);

    List<Event> findByIsFeaturedTrueAndStatusOrderByStartTimeAsc(String status);
}
