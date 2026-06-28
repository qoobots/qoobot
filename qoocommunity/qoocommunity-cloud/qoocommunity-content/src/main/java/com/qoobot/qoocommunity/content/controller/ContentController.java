package com.qoobot.qoocommunity.content.controller;

import com.qoobot.qoocommunity.common.dto.ApiResponse;
import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.content.domain.Blog;
import com.qoobot.qoocommunity.content.domain.Showcase;
import com.qoobot.qoocommunity.content.service.ContentService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/content")
@RequiredArgsConstructor
public class ContentController {

    private final ContentService contentService;

    // ---- Blogs ----

    @GetMapping("/blog")
    public ApiResponse<PageResponse<Blog>> listBlogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(contentService.listBlogs(page, size));
    }

    @GetMapping("/blog/{slug}")
    public ApiResponse<Blog> getBlog(@PathVariable String slug) {
        return ApiResponse.success(contentService.getBlogBySlug(slug));
    }

    @PostMapping("/blog")
    public ApiResponse<Blog> createBlog(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(contentService.createBlog(userId,
                body.get("title"), body.get("slug"), body.get("summary"),
                body.get("content"), body.get("contentHtml")));
    }

    @PutMapping("/blog/{id}/publish")
    public ApiResponse<Blog> publishBlog(@PathVariable Long id) {
        return ApiResponse.success(contentService.publishBlog(id));
    }

    // ---- Showcase ----

    @GetMapping("/showcase")
    public ApiResponse<PageResponse<Showcase>> listShowcases(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(contentService.listShowcases(page, size));
    }

    @GetMapping("/showcase/featured")
    public ApiResponse<PageResponse<Showcase>> listFeaturedShowcases(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.success(contentService.listFeaturedShowcases(page, size));
    }

    @GetMapping("/showcase/{id}")
    public ApiResponse<Showcase> getShowcase(@PathVariable Long id) {
        return ApiResponse.success(contentService.getShowcase(id));
    }

    @PostMapping("/showcase")
    public ApiResponse<Showcase> submitShowcase(
            @RequestHeader("X-User-Id") String userId,
            @RequestBody Map<String, String> body) {
        return ApiResponse.success(contentService.submitShowcase(userId,
                body.get("title"), body.get("description"),
                body.get("coverUrl"), body.get("videoUrl"), body.get("category")));
    }

    @PutMapping("/showcase/{id}/approve")
    public ApiResponse<Showcase> approveShowcase(@PathVariable Long id) {
        return ApiResponse.success(contentService.approveShowcase(id));
    }
}
