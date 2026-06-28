package com.qoobot.qoocommunity.forum.repository;

import com.qoobot.qoocommunity.forum.domain.Like;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface LikeRepository extends JpaRepository<Like, Long> {
    Optional<Like> findByUserIdAndTargetTypeAndTargetId(String userId, String targetType, Long targetId);
    boolean existsByUserIdAndTargetTypeAndTargetId(String userId, String targetType, Long targetId);
    long countByTargetTypeAndTargetId(String targetType, Long targetId);
}
