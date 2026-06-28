package com.qoobot.qoostore.repository;

import com.qoobot.qoostore.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    Optional<Order> findByOrderNo(String orderNo);
    Page<Order> findByUserIdOrderByCreatedAtDesc(UUID userId, Pageable pageable);
    Optional<Order> findByUserIdAndSkillIdAndStatus(UUID userId, Long skillId, String status);
}
