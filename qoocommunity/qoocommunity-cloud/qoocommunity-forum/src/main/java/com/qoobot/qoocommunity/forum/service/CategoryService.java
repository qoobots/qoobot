package com.qoobot.qoocommunity.forum.service;

import com.qoobot.qoocommunity.forum.domain.Category;
import com.qoobot.qoocommunity.forum.repository.CategoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class CategoryService {

    private final CategoryRepository categoryRepository;

    public List<Category> getAllCategories() {
        List<Category> roots = categoryRepository.findByParentIdIsNullOrderBySortOrderAsc();
        for (Category root : roots) {
            List<Category> children = categoryRepository.findByParentIdOrderBySortOrderAsc(root.getId());
            root.setChildren(children);
        }
        return roots;
    }

    public Category getBySlug(String slug) {
        return categoryRepository.findBySlug(slug)
                .orElseThrow(() -> new RuntimeException("Category not found: " + slug));
    }
}
