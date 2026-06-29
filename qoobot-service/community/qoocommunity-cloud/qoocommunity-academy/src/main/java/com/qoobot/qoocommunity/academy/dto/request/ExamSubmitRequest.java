package com.qoobot.qoocommunity.academy.dto.request;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ExamSubmitRequest {

    private Long certificationId;
    private List<Map<String, String>> answers;
    private Integer score;
}
