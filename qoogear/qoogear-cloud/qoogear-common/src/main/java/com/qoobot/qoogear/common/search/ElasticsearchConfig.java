package com.qoobot.qoogear.common.search;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.rest_client.RestClientTransport;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.http.HttpHost;
import org.elasticsearch.client.RestClient;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Elasticsearch search configuration.
 * Used for full-text search of certified accessories, standards, and reference designs.
 * Falls back to JPA LIKE queries when ES is not available.
 */
@Slf4j
@Configuration
@ConfigurationProperties(prefix = "qoogear.search.elasticsearch")
@ConditionalOnProperty(prefix = "qoogear.search.elasticsearch", name = "enabled", havingValue = "true", matchIfMissing = false)
@Data
public class ElasticsearchConfig {

    private String host = "localhost";
    private int port = 9200;
    private String scheme = "http";

    @Bean
    public ElasticsearchClient elasticsearchClient() {
        log.info("Initializing Elasticsearch client: {}://{}:{}", scheme, host, port);
        RestClient restClient = RestClient.builder(new HttpHost(host, port, scheme)).build();
        ElasticsearchTransport transport = new RestClientTransport(restClient, new JacksonJsonpMapper());
        return new ElasticsearchClient(transport);
    }

    // Index name constants
    public static final String INDEX_CERTIFIED_ACCESSORIES = "qoogear-certified-accessories";
    public static final String INDEX_STANDARDS = "qoogear-standards";
    public static final String INDEX_REFERENCE_DESIGNS = "qoogear-reference-designs";
}
