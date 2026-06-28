package com.qoobot.qoocommunity.forum.repository;

import com.qoobot.qoocommunity.forum.domain.Topic;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface TopicRepository extends JpaRepository<Topic, Long> {

    Page<Topic> findByCategoryIdOrderByCreatedAtDesc(Long categoryId, Pageable pageable);

    @Query("SELECT t FROM Topic t ORDER BY t.likeCount + t.replyCount * 2 + t.viewCount * 0.1 DESC")
    Page<Topic> findHotTopics(Pageable pageable);

    List<Topic> findByUserIdOrderByCreatedAtDesc(String userId);

    @Query("SELECT t FROM Topic t WHERE LOWER(t.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(t.content) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    Page<Topic> searchByKeyword(@Param("keyword") String keyword, Pageable pageable);

    long countByUserId(String userId);
}
