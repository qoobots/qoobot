package com.qoobot.qoocommunity.forum.service;

import com.qoobot.qoocommunity.common.dto.PageResponse;
import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.forum.domain.*;
import com.qoobot.qoocommunity.forum.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class TopicService {

    private final TopicRepository topicRepository;
    private final ReplyRepository replyRepository;
    private final CategoryRepository categoryRepository;
    private final LikeRepository likeRepository;
    private final BookmarkRepository bookmarkRepository;

    public PageResponse<Topic> listByCategory(Long categoryId, int page, int size) {
        Page<Topic> result = topicRepository.findByCategoryIdOrderByCreatedAtDesc(categoryId, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Topic> listHot(int page, int size) {
        Page<Topic> result = topicRepository.findHotTopics(PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public PageResponse<Topic> search(String keyword, int page, int size) {
        Page<Topic> result = topicRepository.searchByKeyword(keyword, PageRequest.of(page, size));
        return PageResponse.of(result.getContent(), result.getTotalElements(), page, size);
    }

    public Topic getTopic(Long id) {
        Topic topic = topicRepository.findById(id)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found: " + id));
        topic.setViewCount(topic.getViewCount() + 1);
        topicRepository.save(topic);
        return topic;
    }

    @Transactional
    public Topic createTopic(String userId, Long categoryId, String title, String content, String contentHtml) {
        if (!categoryRepository.existsById(categoryId)) {
            throw QooCommunityException.badRequest("Category not found");
        }
        Topic topic = new Topic();
        topic.setUserId(userId);
        topic.setCategoryId(categoryId);
        topic.setTitle(title);
        topic.setContent(content);
        topic.setContentHtml(contentHtml);
        topic.setCreatedAt(LocalDateTime.now());
        topic.setUpdatedAt(LocalDateTime.now());
        Topic saved = topicRepository.save(topic);

        categoryRepository.findById(categoryId).ifPresent(cat -> {
            cat.setTopicCount((cat.getTopicCount() == null ? 0 : cat.getTopicCount()) + 1);
            categoryRepository.save(cat);
        });

        return saved;
    }

    @Transactional
    public Topic updateTopic(Long topicId, String userId, String title, String content, String contentHtml) {
        Topic topic = topicRepository.findById(topicId)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found"));
        if (!topic.getUserId().equals(userId)) {
            throw QooCommunityException.forbidden("Not the topic owner");
        }
        topic.setTitle(title);
        topic.setContent(content);
        topic.setContentHtml(contentHtml);
        topic.setUpdatedAt(LocalDateTime.now());
        return topicRepository.save(topic);
    }

    @Transactional
    public void deleteTopic(Long topicId, String userId) {
        Topic topic = topicRepository.findById(topicId)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found"));
        if (!topic.getUserId().equals(userId)) {
            throw QooCommunityException.forbidden("Not the topic owner");
        }
        topicRepository.delete(topic);
    }

    // ---- Replies ----

    public List<Reply> getReplies(Long topicId) {
        return replyRepository.findByTopicIdOrderByCreatedAtAsc(topicId);
    }

    @Transactional
    public Reply createReply(Long topicId, String userId, Long parentId, String content, String contentHtml) {
        Topic topic = topicRepository.findById(topicId)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found"));
        if (topic.getIsLocked()) {
            throw QooCommunityException.badRequest("Topic is locked");
        }
        Reply reply = new Reply();
        reply.setTopicId(topicId);
        reply.setUserId(userId);
        reply.setParentId(parentId);
        reply.setContent(content);
        reply.setContentHtml(contentHtml);
        reply.setCreatedAt(LocalDateTime.now());
        reply.setUpdatedAt(LocalDateTime.now());
        Reply saved = replyRepository.save(reply);

        topic.setReplyCount(replyRepository.countByTopicId(topicId));
        topic.setLastReplyAt(LocalDateTime.now());
        topicRepository.save(topic);

        return saved;
    }

    // ---- Likes ----

    @Transactional
    public void toggleLike(String userId, String targetType, Long targetId) {
        likeRepository.findByUserIdAndTargetTypeAndTargetId(userId, targetType, targetId)
                .ifPresentOrElse(
                        like -> likeRepository.delete(like),
                        () -> {
                            Like like = new Like();
                            like.setUserId(userId);
                            like.setTargetType(targetType);
                            like.setTargetId(targetId);
                            likeRepository.save(like);
                        }
                );

        long count = likeRepository.countByTargetTypeAndTargetId(targetType, targetId);
        if ("TOPIC".equals(targetType)) {
            topicRepository.findById(targetId).ifPresent(t -> {
                t.setLikeCount((int) count);
                topicRepository.save(t);
            });
        }
    }

    public boolean isLiked(String userId, String targetType, Long targetId) {
        return likeRepository.existsByUserIdAndTargetTypeAndTargetId(userId, targetType, targetId);
    }

    // ---- Bookmarks ----

    @Transactional
    public void toggleBookmark(String userId, Long topicId) {
        bookmarkRepository.findByUserIdAndTopicId(userId, topicId)
                .ifPresentOrElse(
                        b -> bookmarkRepository.delete(b),
                        () -> {
                            Bookmark bm = new Bookmark();
                            bm.setUserId(userId);
                            bm.setTopicId(topicId);
                            bookmarkRepository.save(bm);
                        }
                );
    }

    public boolean isBookmarked(String userId, Long topicId) {
        return bookmarkRepository.existsByUserIdAndTopicId(userId, topicId);
    }

    public List<Bookmark> getUserBookmarks(String userId) {
        return bookmarkRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }
}
