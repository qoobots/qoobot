package com.qoobot.qoocommunity.forum.dto.request;

import lombok.Data;

@Data
public class SearchRequest {

    private String keyword;

    private Long categoryId;

    private String sort;

    private int page = 0;

    private int size = 20;
}
