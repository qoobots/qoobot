package com.qoobot.qoostore.service;

import com.qoobot.qoostore.dto.response.OrderResponse;
import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class CommerceService {

    private static final BigDecimal DEFAULT_SHARE_RATE = new BigDecimal("0.7000");
    private static final BigDecimal HIGH_VOLUME_SHARE_RATE = new BigDecimal("0.8500");
    private static final BigDecimal HIGH_VOLUME_THRESHOLD = new BigDecimal("1000000.00");

    private final OrderRepository orderRepository;
    private final SkillRepository skillRepository;
    private final LicenseRepository licenseRepository;
    private final DeveloperRevenueRepository revenueRepository;
    private final DeveloperRepository developerRepository;

    @Transactional
    public OrderResponse createOrder(UUID userId, String skillId, String paymentMethod) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (!"published".equals(skill.getStatus())) {
            throw new RuntimeException("Skill is not available for purchase");
        }

        String orderNo = generateOrderNo();
        BigDecimal amount = skill.getPrice();
        BigDecimal totalAmount = amount;

        Order order = Order.builder()
                .orderNo(orderNo)
                .userId(userId)
                .skillId(skill.getId())
                .amount(amount)
                .currency(skill.getCurrency())
                .totalAmount(totalAmount)
                .status("pending")
                .paymentMethod(paymentMethod)
                .build();
        order = orderRepository.save(order);

        log.info("Order created: orderNo={}, skillId={}, amount={}", orderNo, skillId, totalAmount);

        return OrderResponse.builder()
                .id(order.getId())
                .orderNo(order.getOrderNo())
                .skillName(skill.getName())
                .amount(order.getAmount())
                .currency(order.getCurrency())
                .totalAmount(order.getTotalAmount())
                .status(order.getStatus())
                .paymentMethod(order.getPaymentMethod())
                .createdAt(order.getCreatedAt())
                .build();
    }

    @Transactional
    public void processPayment(String orderNo, String paymentId) {
        Order order = orderRepository.findByOrderNo(orderNo)
                .orElseThrow(() -> new RuntimeException("Order not found: " + orderNo));

        order.setStatus("paid");
        order.setPaymentId(paymentId);
        order.setPaidAt(LocalDateTime.now());
        orderRepository.save(order);

        Skill skill = skillRepository.findById(order.getSkillId())
                .orElseThrow(() -> new RuntimeException("Skill not found"));

        String licenseKey = generateLicenseKey();
        License license = License.builder()
                .userId(order.getUserId())
                .skillId(order.getSkillId())
                .orderId(order.getId())
                .licenseKey(licenseKey)
                .type("perpetual")
                .status("active")
                .startsAt(LocalDateTime.now())
                .build();
        licenseRepository.save(license);

        BigDecimal shareRate = calculateShareRate(skill.getDeveloperId());
        BigDecimal platformFee = order.getAmount().subtract(
                order.getAmount().multiply(shareRate)).setScale(2, RoundingMode.HALF_UP);
        BigDecimal developerShare = order.getAmount().subtract(platformFee);

        DeveloperRevenue revenue = DeveloperRevenue.builder()
                .developerId(skill.getDeveloperId())
                .orderId(order.getId())
                .skillId(skill.getId())
                .grossAmount(order.getAmount())
                .platformFee(platformFee)
                .developerShare(developerShare)
                .shareRate(shareRate)
                .currency(order.getCurrency())
                .build();
        revenueRepository.save(revenue);

        order.setStatus("completed");
        order.setCompletedAt(LocalDateTime.now());
        orderRepository.save(order);

        log.info("Payment processed: orderNo={}, licenseKey={}, devShare={}", orderNo, licenseKey, developerShare);
    }

    public OrderResponse getOrder(String orderNo) {
        Order order = orderRepository.findByOrderNo(orderNo)
                .orElseThrow(() -> new RuntimeException("Order not found: " + orderNo));

        Skill skill = skillRepository.findById(order.getSkillId())
                .orElse(null);

        return OrderResponse.builder()
                .id(order.getId())
                .orderNo(order.getOrderNo())
                .skillName(skill != null ? skill.getName() : null)
                .amount(order.getAmount())
                .currency(order.getCurrency())
                .totalAmount(order.getTotalAmount())
                .status(order.getStatus())
                .paymentMethod(order.getPaymentMethod())
                .paidAt(order.getPaidAt())
                .createdAt(order.getCreatedAt())
                .build();
    }

    public Page<OrderResponse> getUserOrders(UUID userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return orderRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable)
                .map(order -> {
                    Skill skill = skillRepository.findById(order.getSkillId()).orElse(null);
                    return OrderResponse.builder()
                            .id(order.getId())
                            .orderNo(order.getOrderNo())
                            .skillName(skill != null ? skill.getName() : null)
                            .amount(order.getAmount())
                            .currency(order.getCurrency())
                            .totalAmount(order.getTotalAmount())
                            .status(order.getStatus())
                            .paymentMethod(order.getPaymentMethod())
                            .paidAt(order.getPaidAt())
                            .createdAt(order.getCreatedAt())
                            .build();
                });
    }

    @Transactional
    public void createReview(UUID userId, String skillId, Short rating, String title, String content) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new RuntimeException("Skill not found: " + skillId));

        if (rating < 1 || rating > 5) {
            throw new RuntimeException("Rating must be between 1 and 5");
        }

        Review review = Review.builder()
                .skillId(skill.getId())
                .userId(userId)
                .rating(rating)
                .title(title)
                .content(content)
                .build();
        reviewRepository.save(review);
        log.info("Review created: skillId={}, userId={}, rating={}", skillId, userId, rating);
    }

    private BigDecimal calculateShareRate(Long developerId) {
        BigDecimal lifetimeRevenue = revenueRepository.sumDeveloperShareByDeveloperId(developerId);
        if (lifetimeRevenue != null && lifetimeRevenue.compareTo(HIGH_VOLUME_THRESHOLD) > 0) {
            return HIGH_VOLUME_SHARE_RATE;
        }
        return DEFAULT_SHARE_RATE;
    }

    private String generateOrderNo() {
        return "QSK" + System.currentTimeMillis() + String.format("%04d", (int)(Math.random() * 10000));
    }

    private String generateLicenseKey() {
        return "QSL-" + UUID.randomUUID().toString().replace("-", "").toUpperCase();
    }

    private final ReviewRepository reviewRepository;
}
