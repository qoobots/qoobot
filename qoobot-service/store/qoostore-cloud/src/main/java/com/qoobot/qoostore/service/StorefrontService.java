package com.qoobot.qoostore.service;

import com.qoobot.qoostore.dto.response.*;
import com.qoobot.qoostore.entity.*;
import com.qoobot.qoostore.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class StorefrontService {

    private final SkillRepository skillRepository;
    private final CategoryRepository categoryRepository;
    private final ReviewRepository reviewRepository;
    private final SkillStatsRepository skillStatsRepository;

    @Cacheable(value = "store:skills:list", key = "#page + '-' + #size + '-' + #sortBy")
    public SkillListResponse listSkills(int page, int size, String sortBy) {
        Sort sort = switch (sortBy != null ? sortBy : "newest") {
            case "rating" -> Sort.by("id").descending(); // will be enriched
            case "downloads" -> Sort.by("id").descending();
            default -> Sort.by("publishedAt").descending();
        };
        Pageable pageable = PageRequest.of(page, size, sort);
        Page<Skill> skillPage = skillRepository.findByStatus("published", pageable);

        List<SkillResponse> skills = skillPage.getContent().stream()
                .map(this::toSkillResponse)
                .collect(Collectors.toList());

        return SkillListResponse.builder()
                .skills(skills)
                .page(page)
                .size(size)
                .totalElements(skillPage.getTotalElements())
                .totalPages(skillPage.getTotalPages())
                .build();
    }

    @Cacheable(value = "store:skills:detail", key = "#skillId")
    public SkillResponse getSkillDetail(String skillId) {
        Skill skill = skillRepository.findBySkillId(skillId)
                .orElseThrow(() -> new com.qoobot.qoostore.exception.SkillNotFoundException(skillId));
        return toSkillResponse(skill);
    }

    public SkillListResponse searchSkills(String query, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<Skill> skillPage = skillRepository.searchPublished(query, pageable);

        List<SkillResponse> skills = skillPage.getContent().stream()
                .map(this::toSkillResponse)
                .collect(Collectors.toList());

        return SkillListResponse.builder()
                .skills(skills)
                .page(page)
                .size(size)
                .totalElements(skillPage.getTotalElements())
                .totalPages(skillPage.getTotalPages())
                .build();
    }

    @Cacheable(value = "store:categories:all")
    public List<Category> listCategories() {
        return categoryRepository.findByParentIdIsNullOrderBySortOrder();
    }

    public SkillListResponse listSkillsByCategory(String categorySlug, int page, int size) {
        Category category = categoryRepository.findBySlug(categorySlug)
                .orElseThrow(() -> new RuntimeException("Category not found: " + categorySlug));

        Pageable pageable = PageRequest.of(page, size, Sort.by("publishedAt").descending());
        Page<Skill> skillPage = skillRepository.findByCategoryIdAndStatus(category.getId(), "published", pageable);

        List<SkillResponse> skills = skillPage.getContent().stream()
                .map(this::toSkillResponse)
                .collect(Collectors.toList());

        return SkillListResponse.builder()
                .skills(skills)
                .page(page)
                .size(size)
                .totalElements(skillPage.getTotalElements())
                .totalPages(skillPage.getTotalPages())
                .build();
    }

    @Cacheable(value = "store:skills:featured")
    public List<SkillResponse> getFeaturedSkills() {
        Pageable top10 = PageRequest.of(0, 10, Sort.by("publishedAt").descending());
        return skillRepository.findByStatus("published", top10).getContent().stream()
                .map(this::toSkillResponse)
                .collect(Collectors.toList());
    }

    public SkillListResponse getRankings(String type, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<Skill> skillPage;

        switch (type) {
            case "free" -> skillPage = skillRepository.findByPricingModel("free", pageable);
            case "paid" -> skillPage = skillRepository.findByPricingModel("paid", pageable);
            default -> skillPage = skillRepository.findByStatus("published", pageable);
        }

        List<SkillResponse> skills = skillPage.getContent().stream()
                .map(this::toSkillResponse)
                .collect(Collectors.toList());

        return SkillListResponse.builder()
                .skills(skills)
                .page(page)
                .size(size)
                .totalElements(skillPage.getTotalElements())
                .totalPages(skillPage.getTotalPages())
                .build();
    }

    public Page<ReviewResponse> getSkillReviews(Long skillId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by("createdAt").descending());
        Page<Review> reviewPage = reviewRepository.findBySkillIdAndStatusOrderByCreatedAtDesc(skillId, "published", pageable);
        return reviewPage.map(this::toReviewResponse);
    }

    private SkillResponse toSkillResponse(Skill skill) {
        BigDecimal avgRating = reviewRepository.getAverageRating(skill.getId());
        long reviewCount = reviewRepository.countBySkillId(skill.getId());

        return SkillResponse.builder()
                .id(skill.getId())
                .skillId(skill.getSkillId())
                .name(skill.getName())
                .developerId(skill.getDeveloperId())
                .categoryId(skill.getCategoryId())
                .tagline(skill.getTagline())
                .description(skill.getDescription())
                .iconUrl(skill.getIconUrl())
                .pricingModel(skill.getPricingModel())
                .price(skill.getPrice())
                .currency(skill.getCurrency())
                .trialDays(skill.getTrialDays())
                .status(skill.getStatus())
                .avgRating(avgRating != null ? avgRating.setScale(2, RoundingMode.HALF_UP).doubleValue() : 0.0)
                .reviewCount(reviewCount)
                .downloadCount(0L)
                .publishedAt(skill.getPublishedAt())
                .updatedAt(skill.getUpdatedAt())
                .build();
    }

    private ReviewResponse toReviewResponse(Review review) {
        return ReviewResponse.builder()
                .id(review.getId())
                .skillId(review.getSkillId())
                .rating(review.getRating())
                .title(review.getTitle())
                .content(review.getContent())
                .helpfulCount(review.getHelpfulCount())
                .createdAt(review.getCreatedAt())
                .build();
    }
}
