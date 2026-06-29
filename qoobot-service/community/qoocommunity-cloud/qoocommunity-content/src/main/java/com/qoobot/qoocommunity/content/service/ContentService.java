package com.qoobot.qoocommunity.content.service;

import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.content.domain.Blog;
import com.qoobot.qoocommunity.content.domain.Showcase;
import com.qoobot.qoocommunity.content.repository.BlogRepository;
import com.qoobot.qoocommunity.content.repository.ShowcaseRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class ContentService {

    private final BlogRepository blogRepository;
    private final ShowcaseRepository showcaseRepository;

    // ---- Blogs ----

    public PageResponse<Blog> listBlogs(int page, int size) {
        Page<Blog> result = blogRepository.findByIsPublishedTrueOrderByPublishedAtDesc(PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Blog getBlogBySlug(String slug) {
        return blogRepository.findByIsPublishedTrueOrderByPublishedAtDesc(PageRequest.of(0, Integer.MAX_VALUE))
                .stream()
                .filter(b -> b.getSlug().equals(slug))
                .findFirst()
                .orElseThrow(() -> QooCommunityException.notFound("Blog not found: " + slug));
    }

    @Transactional
    public Blog createBlog(String userId, String title, String slug, String summary,
                            String content, String contentHtml) {
        Blog blog = new Blog();
        blog.setTitle(title);
        blog.setSlug(slug);
        blog.setSummary(summary);
        blog.setContent(content);
        blog.setContentHtml(contentHtml);
        blog.setAuthorId(userId);
        blog.setCreatedAt(LocalDateTime.now());
        blog.setUpdatedAt(LocalDateTime.now());
        return blogRepository.save(blog);
    }

    @Transactional
    public Blog publishBlog(Long blogId) {
        Blog blog = blogRepository.findById(blogId)
                .orElseThrow(() -> QooCommunityException.notFound("Blog not found"));
        blog.setIsPublished(true);
        blog.setPublishedAt(LocalDateTime.now());
        blog.setUpdatedAt(LocalDateTime.now());
        return blogRepository.save(blog);
    }

    // ---- Showcase ----

    public PageResponse<Showcase> listShowcases(int page, int size) {
        Page<Showcase> result = showcaseRepository.findByStatusOrderByCreatedAtDesc("APPROVED", PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Showcase> listFeaturedShowcases(int page, int size) {
        Page<Showcase> result = showcaseRepository.findByIsFeaturedTrueAndStatusOrderByCreatedAtDesc(
                "APPROVED", PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Showcase getShowcase(Long id) {
        Showcase s = showcaseRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Showcase not found: " + id));
        s.setViewCount(s.getViewCount() + 1);
        showcaseRepository.save(s);
        return s;
    }

    @Transactional
    public Showcase submitShowcase(String userId, String title, String description,
                                    String coverUrl, String videoUrl, String category) {
        Showcase s = new Showcase();
        s.setTitle(title);
        s.setDescription(description);
        s.setCoverUrl(coverUrl);
        s.setVideoUrl(videoUrl);
        s.setAuthorId(userId);
        s.setCategory(category);
        s.setStatus("PENDING");
        s.setCreatedAt(LocalDateTime.now());
        s.setUpdatedAt(LocalDateTime.now());
        return showcaseRepository.save(s);
    }

    @Transactional
    public Showcase approveShowcase(Long showcaseId) {
        Showcase s = showcaseRepository.findById(showcaseId)
                .orElseThrow(() -> QooCommunityException.notFound("Showcase not found"));
        s.setStatus("APPROVED");
        s.setUpdatedAt(LocalDateTime.now());
        return showcaseRepository.save(s);
    }
}
