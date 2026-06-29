package com.qoobot.qoostore.service;

import com.qoobot.qoostore.dto.response.SkillListResponse;
import com.qoobot.qoostore.dto.response.SkillResponse;
import com.qoobot.qoostore.entity.Category;
import com.qoobot.qoostore.entity.Skill;
import com.qoobot.qoostore.repository.CategoryRepository;
import com.qoobot.qoostore.repository.ReviewRepository;
import com.qoobot.qoostore.repository.SkillRepository;
import com.qoobot.qoostore.repository.SkillStatsRepository;
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

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class StorefrontServiceTest {

    @Mock
    private SkillRepository skillRepository;

    @Mock
    private CategoryRepository categoryRepository;

    @Mock
    private ReviewRepository reviewRepository;

    @Mock
    private SkillStatsRepository skillStatsRepository;

    @InjectMocks
    private StorefrontService storefrontService;

    private Skill testSkill;

    @BeforeEach
    void setUp() {
        testSkill = Skill.builder()
                .id(1L)
                .skillId("com.test.cleaning")
                .name("智能清洁")
                .developerId(100L)
                .categoryId(1L)
                .tagline("让机器人成为清洁专家")
                .description("AI驱动的全屋清洁技能")
                .iconUrl("https://cdn.qoobot.ai/icons/cleaning.png")
                .pricingModel("free")
                .price(BigDecimal.ZERO)
                .currency("USD")
                .status("published")
                .publishedAt(LocalDateTime.now())
                .build();
    }

    @Test
    void listSkills_shouldReturnPaginatedResults() {
        Page<Skill> skillPage = new PageImpl<>(List.of(testSkill));
        when(skillRepository.findByStatus(eq("published"), any(Pageable.class)))
                .thenReturn(skillPage);
        when(reviewRepository.getAverageRating(anyLong())).thenReturn(BigDecimal.valueOf(4.5));
        when(reviewRepository.countBySkillId(anyLong())).thenReturn(10L);

        SkillListResponse result = storefrontService.listSkills(0, 20, "newest");

        assertThat(result).isNotNull();
        assertThat(result.getSkills()).hasSize(1);
        assertThat(result.getTotalElements()).isEqualTo(1);
        assertThat(result.getSkills().get(0).getSkillId()).isEqualTo("com.test.cleaning");
    }

    @Test
    void getSkillDetail_shouldReturnSkill() {
        when(skillRepository.findBySkillId("com.test.cleaning"))
                .thenReturn(Optional.of(testSkill));
        when(reviewRepository.getAverageRating(anyLong())).thenReturn(BigDecimal.valueOf(4.5));
        when(reviewRepository.countBySkillId(anyLong())).thenReturn(10L);

        SkillResponse result = storefrontService.getSkillDetail("com.test.cleaning");

        assertThat(result).isNotNull();
        assertThat(result.getSkillId()).isEqualTo("com.test.cleaning");
        assertThat(result.getName()).isEqualTo("智能清洁");
        assertThat(result.getAvgRating()).isEqualTo(4.5);
    }

    @Test
    void getSkillDetail_shouldThrowWhenNotFound() {
        when(skillRepository.findBySkillId("nonexistent")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> storefrontService.getSkillDetail("nonexistent"))
                .isInstanceOf(com.qoobot.qoostore.exception.SkillNotFoundException.class);
    }

    @Test
    void searchSkills_shouldReturnMatchingSkills() {
        Page<Skill> skillPage = new PageImpl<>(List.of(testSkill));
        when(skillRepository.searchPublished(eq("清洁"), any(Pageable.class)))
                .thenReturn(skillPage);
        when(reviewRepository.getAverageRating(anyLong())).thenReturn(BigDecimal.valueOf(4.5));
        when(reviewRepository.countBySkillId(anyLong())).thenReturn(10L);

        SkillListResponse result = storefrontService.searchSkills("清洁", 0, 20);

        assertThat(result).isNotNull();
        assertThat(result.getSkills()).hasSize(1);
    }

    @Test
    void listCategories_shouldReturnCategories() {
        Category cat = Category.builder()
                .id(1L).name("家庭").slug("home").build();
        when(categoryRepository.findByParentIdIsNullOrderBySortOrder())
                .thenReturn(List.of(cat));

        List<Category> result = storefrontService.listCategories();

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getSlug()).isEqualTo("home");
    }

    @Test
    void getFeaturedSkills_shouldReturnTop10() {
        Page<Skill> skillPage = new PageImpl<>(List.of(testSkill));
        when(skillRepository.findByStatus(eq("published"), any(Pageable.class)))
                .thenReturn(skillPage);
        when(reviewRepository.getAverageRating(anyLong())).thenReturn(BigDecimal.valueOf(4.5));
        when(reviewRepository.countBySkillId(anyLong())).thenReturn(10L);

        List<SkillResponse> result = storefrontService.getFeaturedSkills();

        assertThat(result).hasSize(1);
    }

    @Test
    void getRankings_free_shouldReturnFreeSkills() {
        Page<Skill> skillPage = new PageImpl<>(List.of(testSkill));
        when(skillRepository.findByPricingModel(eq("free"), any(Pageable.class)))
                .thenReturn(skillPage);
        when(reviewRepository.getAverageRating(anyLong())).thenReturn(BigDecimal.valueOf(4.5));
        when(reviewRepository.countBySkillId(anyLong())).thenReturn(10L);

        SkillListResponse result = storefrontService.getRankings("free", 0, 20);

        assertThat(result).isNotNull();
        assertThat(result.getSkills()).hasSize(1);
    }
}
