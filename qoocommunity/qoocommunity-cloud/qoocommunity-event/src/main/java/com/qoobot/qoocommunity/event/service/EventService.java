package com.qoobot.qoocommunity.event.service;

import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.event.domain.*;
import com.qoobot.qoocommunity.event.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class EventService {

    private final EventRepository eventRepository;
    private final RegistrationRepository registrationRepository;
    private final AgendaItemRepository agendaItemRepository;
    private final EventMaterialRepository materialRepository;

    public PageResponse<Event> listEvents(String status, int page, int size) {
        Page<Event> result = eventRepository.findByStatusOrderByStartTimeAsc(status, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public List<Event> listUpcoming() {
        return eventRepository.findByStartTimeAfterAndStatusOrderByStartTimeAsc(
                LocalDateTime.now(), "PUBLISHED");
    }

    public List<Event> listFeatured() {
        return eventRepository.findByIsFeaturedTrueAndStatusOrderByStartTimeAsc("PUBLISHED");
    }

    public PageResponse<Event> listByType(String type, int page, int size) {
        Page<Event> result = eventRepository.findByTypeOrderByStartTimeDesc(type, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Event getEvent(Long id) {
        return eventRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Event not found: " + id));
    }

    @Transactional
    public Event createEvent(String userId, String title, String type, String description,
                              String location, LocalDateTime startTime, LocalDateTime endTime,
                              Integer maxAttendees) {
        Event event = new Event();
        event.setTitle(title);
        event.setSlug(generateSlug(title));
        event.setType(type);
        event.setDescription(description);
        event.setLocation(location);
        event.setStartTime(startTime);
        event.setEndTime(endTime);
        event.setMaxAttendees(maxAttendees);
        event.setCreatedBy(userId);
        event.setCreatedAt(LocalDateTime.now());
        event.setUpdatedAt(LocalDateTime.now());
        return eventRepository.save(event);
    }

    @Transactional
    public Event publishEvent(Long eventId) {
        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> QooCommunityException.notFound("Event not found"));
        event.setStatus("PUBLISHED");
        event.setUpdatedAt(LocalDateTime.now());
        return eventRepository.save(event);
    }

    @Transactional
    public Registration register(Long eventId, String userId, String name, String company, String email) {
        Event event = eventRepository.findById(eventId)
                .orElseThrow(() -> QooCommunityException.notFound("Event not found"));
        if (!"PUBLISHED".equals(event.getStatus())) {
            throw QooCommunityException.badRequest("Event is not open for registration");
        }
        if (event.getMaxAttendees() != null && event.getCurrentAttendees() >= event.getMaxAttendees()) {
            throw QooCommunityException.badRequest("Event is full");
        }
        if (registrationRepository.findByEventIdAndUserId(eventId, userId).isPresent()) {
            throw QooCommunityException.badRequest("Already registered");
        }

        Registration reg = new Registration();
        reg.setEventId(eventId);
        reg.setUserId(userId);
        reg.setName(name);
        reg.setCompany(company);
        reg.setEmail(email);
        Registration saved = registrationRepository.save(reg);

        event.setCurrentAttendees((int) registrationRepository.countByEventId(eventId));
        eventRepository.save(event);

        return saved;
    }

    @Transactional
    public void cancelRegistration(Long eventId, String userId) {
        Registration reg = registrationRepository.findByEventIdAndUserId(eventId, userId)
                .orElseThrow(() -> QooCommunityException.notFound("Registration not found"));
        registrationRepository.delete(reg);

        eventRepository.findById(eventId).ifPresent(event -> {
            event.setCurrentAttendees((int) registrationRepository.countByEventId(eventId));
            eventRepository.save(event);
        });
    }

    public List<Registration> getAttendees(Long eventId) {
        return registrationRepository.findByEventId(eventId);
    }

    public List<AgendaItem> getAgenda(Long eventId) {
        return agendaItemRepository.findByEventIdOrderBySortOrderAsc(eventId);
    }

    public List<EventMaterial> getMaterials(Long eventId) {
        return materialRepository.findByEventId(eventId);
    }

    private String generateSlug(String title) {
        return title.toLowerCase().replaceAll("[^a-z0-9\\u4e00-\\u9fff]+", "-")
                .replaceAll("^-|-$", "") + "-" + System.currentTimeMillis() % 100000;
    }
}
