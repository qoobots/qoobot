package com.qoobot.qoogear.common.dto;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for ApiResponse and PageResponse.
 */
class ApiResponseTest {

    @Test
    void shouldCreateSuccessResponse() {
        ApiResponse<String> response = ApiResponse.success("hello");
        assertEquals(200, response.getCode());
        assertEquals("success", response.getMessage());
        assertEquals("hello", response.getData());
        assertNotNull(response.getTimestamp());
    }

    @Test
    void shouldCreateSuccessResponseWithCustomMessage() {
        ApiResponse<String> response = ApiResponse.success("Created", "hello");
        assertEquals(200, response.getCode());
        assertEquals("Created", response.getMessage());
    }

    @Test
    void shouldCreateErrorResponse() {
        ApiResponse<Void> response = ApiResponse.error(404, "Not found");
        assertEquals(404, response.getCode());
        assertEquals("Not found", response.getMessage());
        assertNull(response.getData());
    }

    @Test
    void shouldCreatePageResponse() {
        PageResponse<String> page = PageResponse.of(
                java.util.List.of("a", "b", "c"),
                100L, 0, 20);
        assertEquals(3, page.getItems().size());
        assertEquals(100L, page.getTotal());
        assertEquals(0, page.getPage());
        assertEquals(20, page.getSize());
        assertEquals(5, page.getTotalPages());
    }

    @Test
    void shouldCalculateTotalPagesCorrectly() {
        PageResponse<String> page = PageResponse.of(
                java.util.List.of("a"),
                25L, 0, 10);
        assertEquals(3, page.getTotalPages());
    }
}
