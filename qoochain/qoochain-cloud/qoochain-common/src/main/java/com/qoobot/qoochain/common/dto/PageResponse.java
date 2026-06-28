package com.qoobot.qoochain.common.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResponse<T> {
    private List<T> content;
    private int page;
    private int size;
    private long totalElements;
    private int totalPages;
    private boolean hasNext;
    private boolean hasPrevious;

    public static <T> PageResponse<T> of(List<T> content, int page, int size, long totalElements) {
        PageResponse<T> response = new PageResponse<>();
        response.content = content;
        response.page = page;
        response.size = size;
        response.totalElements = totalElements;
        response.totalPages = size > 0 ? (int) Math.ceil((double) totalElements / size) : 0;
        response.hasNext = (long) (page + 1) * size < totalElements;
        response.hasPrevious = page > 0;
        return response;
    }
}
