package com.qoobot.qoocommunity.event.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.event.domain.*;
import com.qoobot.qoocommunity.event.dto.request.EventCreateRequest;
import com.qoobot.qoocommunity.event.dto.request.RegistrationRequest;
import com.qoobot.qoocommunity.event.service.EventService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/events")
@RequiredArgsConstructor
public class EventController {

    private final EventService eventService;

    @GetMapping
    public ApiResponse<PageResponse<Event>> listEvents(
            @RequestParam(defaultValue = "PUBLISHED") String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(eventService.listEvents(status, page, size));
    }

    @GetMapping("/upcoming")
    public ApiResponse<List<Event>> listUpcoming() {
        return ApiResponse.success(eventService.listUpcoming());
    }

    @GetMapping("/featured")
    public ApiResponse<List<Event>> listFeatured() {
        return ApiResponse.success(eventService.listFeatured());
    }

    @GetMapping("/type/{type}")
    public ApiResponse<PageResponse<Event>> listByType(
            @PathVariable String type,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(eventService.listByType(type.toUpperCase(), page, size));
    }

    @GetMapping("/{id}")
    public ApiResponse<Event> getEvent(@PathVariable Long id) {
        return ApiResponse.success(eventService.getEvent(id));
    }

    @PostMapping
    public ApiResponse<Event> createEvent(
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody EventCreateRequest body) {
        return ApiResponse.success(eventService.createEvent(userId,
                body.getTitle(),
                body.getType() != null ? body.getType().name() : null,
                body.getDescription(),
                body.getLocation(),
                body.getStartTime(),
                body.getEndTime(),
                body.getMaxAttendees()));
    }

    @PutMapping("/{id}/publish")
    public ApiResponse<Event> publishEvent(@PathVariable Long id) {
        return ApiResponse.success(eventService.publishEvent(id));
    }

    @PutMapping("/{id}/cancel")
    public ApiResponse<Event> cancelEvent(@PathVariable Long id) {
        return ApiResponse.success(eventService.cancelEvent(id));
    }

    @PostMapping("/{id}/register")
    public ApiResponse<Registration> register(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody RegistrationRequest body) {
        return ApiResponse.success(eventService.register(id, userId,
                body.getName(), body.getCompany(), body.getEmail()));
    }

    @DeleteMapping("/{id}/register")
    public ApiResponse<Void> cancelRegistration(
            @PathVariable Long id, @RequestHeader("X-User-Id") String userId) {
        eventService.cancelRegistration(id, userId);
        return ApiResponse.success("Cancelled", null);
    }

    @GetMapping("/{id}/attendees")
    public ApiResponse<List<Registration>> getAttendees(@PathVariable Long id) {
        return ApiResponse.success(eventService.getAttendees(id));
    }

    @GetMapping("/{id}/agenda")
    public ApiResponse<List<AgendaItem>> getAgenda(@PathVariable Long id) {
        return ApiResponse.success(eventService.getAgenda(id));
    }

    @GetMapping("/{id}/materials")
    public ApiResponse<List<EventMaterial>> getMaterials(@PathVariable Long id) {
        return ApiResponse.success(eventService.getMaterials(id));
    }
}
