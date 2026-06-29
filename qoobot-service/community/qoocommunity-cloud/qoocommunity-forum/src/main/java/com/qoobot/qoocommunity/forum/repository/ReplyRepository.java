package com.qoobot.qoocommunity.forum.repository;

import com.qoobot.qoocommunity.forum.domain.Reply;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReplyRepository extends JpaRepository<Reply, Long> {

    List<Reply> findByTopicIdOrderByCreatedAtAsc(Long topicId);

    long countByTopicId(Long topicId);

    long countByUserId(String userId);
}
