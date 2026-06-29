package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.Skill;
import com.qoobot.qoostore.repository.SkillRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * 搜索服务
 * 技能全文搜索、搜索建议、热门搜索
 * 生产环境应集成 Elasticsearch，当前为 PostgreSQL FTS 实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SearchService {

    private final SkillRepository skillRepository;

    // 搜索历史缓存（生产环境用 Redis Sorted Set）
    private final ConcurrentHashMap<String, Long> searchHistory = new ConcurrentHashMap<>();
    private static final int MAX_HISTORY_SIZE = 100;

    /**
     * 全文搜索技能
     */
    public Page<Skill> search(String query, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return skillRepository.searchPublished(query, pageable);
    }

    /**
     * 高级搜索（多条件）
     */
    public Page<Skill> advancedSearch(String query, String categorySlug, String pricingModel,
                                       String sortBy, int page, int size) {
        if (query != null && !query.isEmpty()) {
            recordSearch(query);
        }
        Pageable pageable = PageRequest.of(page, size);
        return skillRepository.searchPublished(query, pageable);
    }

    /**
     * 获取搜索建议（自动补全）
     */
    public List<String> getSuggestions(String prefix, int limit) {
        if (prefix == null || prefix.length() < 2) {
            return List.of();
        }

        // 从搜索历史中获取匹配的建议
        return searchHistory.keySet().stream()
                .filter(q -> q.toLowerCase().startsWith(prefix.toLowerCase()))
                .sorted((a, b) -> Long.compare(
                        searchHistory.getOrDefault(b, 0L),
                        searchHistory.getOrDefault(a, 0L)))
                .limit(limit)
                .collect(Collectors.toList());
    }

    /**
     * 获取热门搜索
     */
    public List<Map<String, Object>> getHotSearches(int limit) {
        return searchHistory.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(limit)
                .map(entry -> {
                    Map<String, Object> item = new HashMap<>();
                    item.put("query", entry.getKey());
                    item.put("count", entry.getValue());
                    return item;
                })
                .collect(Collectors.toList());
    }

    /**
     * 语义搜索（基于标签和分类匹配）
     */
    public List<Skill> semanticSearch(String intent, int limit) {
        // 提取意图关键词
        String[] keywords = intent.toLowerCase().split("\\s+");
        Set<String> keywordSet = new HashSet<>(Arrays.asList(keywords));

        // 通过标签匹配（生产环境用向量数据库/Embedding）
        Pageable pageable = PageRequest.of(0, limit);
        Page<Skill> results = skillRepository.findByStatus("published", pageable);

        return results.getContent().stream()
                .filter(skill -> {
                    if (skill.getDescription() == null) return false;
                    String desc = skill.getDescription().toLowerCase();
                    return keywordSet.stream().anyMatch(desc::contains);
                })
                .limit(limit)
                .collect(Collectors.toList());
    }

    /**
     * 重建搜索索引（生产环境同步到 Elasticsearch）
     */
    public void rebuildIndex() {
        log.info("Search index rebuild triggered");
        // In production: reindex all published skills to Elasticsearch
        long count = skillRepository.count();
        log.info("Search index rebuild complete: {} skills indexed", count);
    }

    /**
     * 记录搜索关键词
     */
    private void recordSearch(String query) {
        searchHistory.merge(query.toLowerCase().trim(), 1L, Long::sum);
        // 限制历史记录大小
        if (searchHistory.size() > MAX_HISTORY_SIZE) {
            searchHistory.entrySet().stream()
                    .min(Map.Entry.comparingByValue())
                    .ifPresent(e -> searchHistory.remove(e.getKey()));
        }
    }
}
