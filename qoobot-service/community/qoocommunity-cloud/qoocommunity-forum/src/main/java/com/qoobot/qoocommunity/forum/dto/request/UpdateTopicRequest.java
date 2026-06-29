package com.qoobot.qoocommunity.forum.dto.request;

import lombok.Data;

@Data
public class UpdateTopicRequest {
    private String title;
    private String content;
    private String contentHtml;
}
