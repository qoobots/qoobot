package com.qoobot.qoocommunity.qa.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.qa.domain.Answer;
import com.qoobot.qoocommunity.qa.domain.Question;
import com.qoobot.qoocommunity.qa.dto.request.AcceptAnswerRequest;
import com.qoobot.qoocommunity.qa.dto.request.AnswerCreateRequest;
import com.qoobot.qoocommunity.qa.dto.request.QuestionCreateRequest;
import com.qoobot.qoocommunity.qa.service.QuestionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/qa")
@RequiredArgsConstructor
public class QaController {

    private final QuestionService questionService;

    @GetMapping("/questions")
    public ApiResponse<PageResponse<Question>> listQuestions(
            @RequestParam(required = false) String filter,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        if ("unanswered".equals(filter)) {
            return ApiResponse.success(questionService.listUnanswered(page, size));
        }
        return ApiResponse.success(questionService.listQuestions(page, size));
    }

    @GetMapping("/questions/{id}")
    public ApiResponse<Question> getQuestion(@PathVariable Long id) {
        return ApiResponse.success(questionService.getQuestion(id));
    }

    @PostMapping("/questions")
    public ApiResponse<Question> createQuestion(
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody QuestionCreateRequest body) {
        return ApiResponse.success(questionService.createQuestion(userId,
                body.getTitle(), body.getContent(), body.getContentHtml()));
    }

    @GetMapping("/questions/{id}/answers")
    public ApiResponse<List<Answer>> getAnswers(@PathVariable Long id) {
        return ApiResponse.success(questionService.getAnswers(id));
    }

    @PostMapping("/questions/{id}/answer")
    public ApiResponse<Answer> createAnswer(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody AnswerCreateRequest body) {
        return ApiResponse.success(questionService.createAnswer(id, userId,
                body.getContent(), body.getContentHtml()));
    }

    @PostMapping("/answers/{answerId}/accept")
    public ApiResponse<Void> acceptAnswer(
            @PathVariable Long answerId,
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody AcceptAnswerRequest body) {
        questionService.acceptAnswer(body.getQuestionId(), answerId, userId);
        return ApiResponse.success("Accepted", null);
    }

    @PostMapping("/{type}/{targetId}/vote")
    public ApiResponse<Void> vote(
            @PathVariable String type,
            @PathVariable Long targetId,
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        questionService.vote(userId, type.toUpperCase(), targetId, body.get("voteType"));
        return ApiResponse.success("OK", null);
    }

    @GetMapping("/search")
    public ApiResponse<PageResponse<Question>> search(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(questionService.search(q, page, size));
    }
}
