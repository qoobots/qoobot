package com.qoobot.qoogear.common.search;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.Result;
import co.elastic.clients.elasticsearch.core.*;
import co.elastic.clients.elasticsearch.core.search.Hit;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Elasticsearch search service — full-text search across certified accessories, standards, and reference designs.
 * Gracefully degrades when ES is not available.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@ConditionalOnBean(ElasticsearchConfig.class)
public class ElasticsearchSearchService {

    private final ElasticsearchClient esClient;

    /**
     * Index a document into the specified index.
     */
    public boolean indexDocument(String index, String docId, Map<String, Object> document) {
        try {
            IndexResponse response = esClient.index(i -> i
                    .index(index)
                    .id(docId)
                    .document(document));
            boolean success = response.result() == Result.Created || response.result() == Result.Updated;
            log.debug("ES index: index={}, id={}, result={}", index, docId, response.result());
            return success;
        } catch (IOException e) {
            log.error("ES index failed: index={}, id={}", index, docId, e);
            return false;
        }
    }

    /**
     * Delete a document from the specified index.
     */
    public boolean deleteDocument(String index, String docId) {
        try {
            DeleteResponse response = esClient.delete(d -> d.index(index).id(docId));
            log.debug("ES delete: index={}, id={}, result={}", index, docId, response.result());
            return true;
        } catch (IOException e) {
            log.error("ES delete failed: index={}, id={}", index, docId, e);
            return false;
        }
    }

    /**
     * Full-text search across an index.
     */
    public List<Map<String, Object>> search(String index, String query, int from, int size) {
        try {
            SearchResponse<Map> response = esClient.search(s -> s
                            .index(index)
                            .from(from)
                            .size(size)
                            .query(q -> q
                                    .multiMatch(mm -> mm
                                            .query(query)
                                            .fields("title^3", "description^2", "productName^2", "category", "specNumber"))),
                    Map.class);

            return response.hits().hits().stream()
                    .map(Hit::source)
                    .collect(Collectors.toList());
        } catch (IOException e) {
            log.error("ES search failed: index={}, query={}", index, query, e);
            return List.of();
        }
    }

    /**
     * Get total hit count for a search query.
     */
    public long countSearch(String index, String query) {
        try {
            SearchResponse<Map> response = esClient.search(s -> s
                            .index(index)
                            .size(0)
                            .query(q -> q
                                    .multiMatch(mm -> mm
                                            .query(query)
                                            .fields("title", "description", "productName"))),
                    Map.class);
            return response.hits().total() != null ? response.hits().total().value() : 0;
        } catch (IOException e) {
            log.error("ES count failed: index={}, query={}", index, query, e);
            return 0;
        }
    }

    /**
     * Check if ES cluster is healthy.
     */
    public boolean isHealthy() {
        try {
            return esClient.ping().value();
        } catch (IOException e) {
            return false;
        }
    }
}
