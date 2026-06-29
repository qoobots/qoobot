package com.qoobot.qoostore.service;

import com.qoobot.qoostore.dto.response.OrderResponse;
import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class CommerceServiceTest {

    @Mock private OrderRepository orderRepository;
    @Mock private SkillRepository skillRepository;
    @Mock private LicenseRepository licenseRepository;
    @Mock private DeveloperRevenueRepository revenueRepository;
    @Mock private DeveloperRepository developerRepository;
    @Mock private ReviewRepository reviewRepository;

    @InjectMocks
    private CommerceService commerceService;

    private Skill testSkill;
    private UUID testUserId;

    @BeforeEach
    void setUp() {
        testUserId = UUID.randomUUID();
        testSkill = Skill.builder()
                .id(1L)
                .skillId("com.test.cleaning")
                .name("智能清洁")
                .developerId(100L)
                .price(BigDecimal.valueOf(9.99))
                .currency("USD")
                .status("published")
                .build();
    }

    @Test
    void createOrder_shouldCreateOrderSuccessfully() {
        when(skillRepository.findBySkillId("com.test.cleaning"))
                .thenReturn(Optional.of(testSkill));
        when(orderRepository.save(any(Order.class)))
                .thenAnswer(inv -> {
                    Order order = inv.getArgument(0);
                    order.setId(1L);
                    return order;
                });

        OrderResponse result = commerceService.createOrder(testUserId, "com.test.cleaning", "stripe");

        assertThat(result).isNotNull();
        assertThat(result.getOrderNo()).startsWith("QSK");
        assertThat(result.getAmount()).isEqualByComparingTo(BigDecimal.valueOf(9.99));
        assertThat(result.getStatus()).isEqualTo("pending");
        assertThat(result.getPaymentMethod()).isEqualTo("stripe");
    }

    @Test
    void createOrder_shouldFailWhenSkillNotPublished() {
        testSkill.setStatus("draft");
        when(skillRepository.findBySkillId("com.test.cleaning"))
                .thenReturn(Optional.of(testSkill));

        assertThatThrownBy(() -> commerceService.createOrder(testUserId, "com.test.cleaning", "stripe"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("not available");
    }

    @Test
    void processPayment_shouldGenerateLicenseAndRevenue() {
        Order order = Order.builder()
                .id(1L)
                .orderNo("QSK123")
                .userId(testUserId)
                .skillId(1L)
                .amount(BigDecimal.valueOf(9.99))
                .currency("USD")
                .totalAmount(BigDecimal.valueOf(9.99))
                .status("pending")
                .build();

        when(orderRepository.findByOrderNo("QSK123")).thenReturn(Optional.of(order));
        when(skillRepository.findById(1L)).thenReturn(Optional.of(testSkill));
        when(licenseRepository.save(any(License.class))).thenAnswer(inv -> inv.getArgument(0));
        when(revenueRepository.save(any(DeveloperRevenue.class))).thenAnswer(inv -> inv.getArgument(0));
        when(revenueRepository.sumDeveloperShareByDeveloperId(anyLong()))
                .thenReturn(BigDecimal.ZERO);
        when(orderRepository.save(any(Order.class))).thenAnswer(inv -> inv.getArgument(0));

        commerceService.processPayment("QSK123", "pi_test123");

        verify(licenseRepository).save(any(License.class));
        verify(revenueRepository).save(any(DeveloperRevenue.class));
    }

    @Test
    void createReview_shouldCreateReviewSuccessfully() {
        when(skillRepository.findBySkillId("com.test.cleaning"))
                .thenReturn(Optional.of(testSkill));
        when(reviewRepository.save(any(Review.class))).thenAnswer(inv -> inv.getArgument(0));

        commerceService.createReview(testUserId, "com.test.cleaning", (short) 5,
                "很棒", "非常好用的技能");

        verify(reviewRepository).save(any(Review.class));
    }

    @Test
    void createReview_shouldFailWithInvalidRating() {
        when(skillRepository.findBySkillId("com.test.cleaning"))
                .thenReturn(Optional.of(testSkill));

        assertThatThrownBy(() -> commerceService.createReview(testUserId, "com.test.cleaning", (short) 6,
                "test", "test"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("between 1 and 5");
    }
}
