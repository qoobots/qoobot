package com.qoobot.qoocommunity.forum.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.forum.domain.*;
import com.qoobot.qoocommunity.forum.dto.request.ReplyCreateRequest;
import com.qoobot.qoocommunity.forum.dto.request.TopicCreateRequest;
import com.qoobot.qoocommunity.forum.dto.request.UpdateTopicRequest;
import com.qoobot.qoocommunity.forum.service.CategoryService;
import com.qoobot.qoocommunity.forum.service.TopicService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/forums")
@RequiredArgsConstructor
public class ForumController {

    private final CategoryService categoryService;
    private final TopicService topicService;

    // ---- Categories ----

    @GetMapping("/categories")
    public ApiResponse<List<Category>> getCategories() {
        return ApiResponse.success(categoryService.getAllCategories());
    }

    @GetMapping("/categories/{slug}")
    public ApiResponse<Category> getCategory(@PathVariable String slug) {
        return ApiResponse.success(categoryService.getBySlug(slug));
    }

    // ---- Topics ----

    @GetMapping("/topics")
    public ApiResponse<PageResponse<Topic>> listTopics(
            @RequestParam(required = false) Long categoryId,
            @RequestParam(required = false) String sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        if (categoryId != null) {
            return ApiResponse.success(topicService.listByCategory(categoryId, page, size));
        }
        if ("hot".equals(sort)) {
            return ApiResponse.success(topicService.listHot(page, size));
        }
        return ApiResponse.success(topicService.listByCategory(null, page, size));
    }

    @GetMapping("/topics/{id}")
    public ApiResponse<Topic> getTopic(@PathVariable Long id) {
        return ApiResponse.success(topicService.getTopic(id));
    }

    @PostMapping("/topics")
    public ApiResponse<Topic> createTopic(
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody TopicCreateRequest body) {
        return ApiResponse.success(topicService.createTopic(
                userId,
                body.getCategoryId(),
                body.getTitle(),
                body.getContent(),
                body.getContentHtml()));
    }

    @PutMapping("/topics/{id}")
    public ApiResponse<Topic> updateTopic(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody UpdateTopicRequest body) {
        return ApiResponse.success(topicService.updateTopic(id, userId,
                body.getTitle(), body.getContent(), body.getContentHtml()));
    }

    @DeleteMapping("/topics/{id}")
    public ApiResponse<Void> deleteTopic(
            @PathVariable Long id, @RequestHeader("X-User-Id") String userId) {
        topicService.deleteTopic(id, userId);
        return ApiResponse.success("Deleted", null);
    }

    // ---- Replies ----

    @GetMapping("/topics/{id}/replies")
    public ApiResponse<List<Reply>> getReplies(@PathVariable Long id) {
        return ApiResponse.success(topicService.getReplies(id));
    }

    @PostMapping("/topics/{id}/reply")
    public ApiResponse<Reply> createReply(
            @PathVariable Long id,
            @RequestHeader("X-User-Id") String userId,
            @Valid @RequestBody ReplyCreateRequest body) {
        return ApiResponse.success(topicService.createReply(id, userId, body.getParentId(),
                body.getContent(), body.getContentHtml()));
    }

    // ---- Likes ----

    @PostMapping("/{type}/{targetId}/like")
    public ApiResponse<Void> toggleLike(
            @PathVariable String type,
            @PathVariable Long targetId,
            @RequestHeader("X-User-Id") String userId) {
        topicService.toggleLike(userId, type.toUpperCase(), targetId);
        return ApiResponse.success("OK", null);
    }

    @GetMapping("/{type}/{targetId}/liked")
    public ApiResponse<Boolean> isLiked(
            @PathVariable String type,
            @PathVariable Long targetId,
            @RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(topicService.isLiked(userId, type.toUpperCase(), targetId));
    }

    // ---- Bookmarks ----

    @PostMapping("/topics/{id}/bookmark")
    public ApiResponse<Void> toggleBookmark(
            @PathVariable Long id, @RequestHeader("X-User-Id") String userId) {
        topicService.toggleBookmark(userId, id);
        return ApiResponse.success("OK", null);
    }

    @GetMapping("/bookmarks")
    public ApiResponse<List<Bookmark>> getBookmarks(@RequestHeader("X-User-Id") String userId) {
        return ApiResponse.success(topicService.getUserBookmarks(userId));
    }

    // ---- Search ----

    @GetMapping("/search")
    public ApiResponse<PageResponse<Topic>> search(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(topicService.search(q, page, size));
    }
}
