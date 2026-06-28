package com.qoobot.qoocommunity.event.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.event.domain.*;
import com.qoobot.qoocommunity.event.service.EventService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

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
            @RequestBody Map<String, Object> body) {
        return ApiResponse.success(eventService.createEvent(userId,
                (String) body.get("title"), (String) body.get("type"),
                (String) body.get("description"), (String) body.get("location"),
                java.time.LocalDateTime.parse((String) body.get("startTime")),
                java.time.LocalDateTime.parse((String) body.get("endTime")),
                body.get("maxAttendees") != null ? Integer.valueOf(body.get("maxAttendees").toString()) : null));
    }

    @PutMapping("/{id}/publish")
    public ApiResponse<Event> publishEvent(@PathVariable Long id) {
        return ApiResponse.success(eventService.publishEvent(id));
    }

    @PostMapping("/{id}/register")
    public ApiResponse<Registration> register(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(eventService.register(id, userId,
                body.get("name"), body.get("company"), body.get("email")));
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
