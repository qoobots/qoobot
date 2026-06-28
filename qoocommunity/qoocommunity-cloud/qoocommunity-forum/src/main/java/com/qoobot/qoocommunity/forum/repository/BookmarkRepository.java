package com.qoobot.qoocommunity.forum.repository;

import com.qoobot.qoocommunity.forum.domain.Bookmark;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface BookmarkRepository extends JpaRepository<Bookmark, Long> {
    List<Bookmark> findByUserIdOrderByCreatedAtDesc(String userId);
    Optional<Bookmark> findByUserIdAndTopicId(String userId, Long topicId);
    boolean existsByUserIdAndTopicId(String userId, Long topicId);
}
