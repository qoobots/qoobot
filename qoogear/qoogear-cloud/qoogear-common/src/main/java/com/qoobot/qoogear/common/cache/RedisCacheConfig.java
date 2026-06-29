package com.qoobot.qoogear.common.cache;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * Redis cache configuration — per-service TTLs for qoogear entities.
 * Defined TTLs follow 04数据设计.md:
 *   cert:list     5 min   — certification list queries
 *   cert:detail   30 min  — certification detail
 *   standard:list 10 min  — standard specifications
 *   standard:detail 1 hr  — standard detail
 *   developer:profile 15 min — developer profile
 *   lab:equipment  5 min  — laboratory equipment
 *   audit:log      2 min  — audit logs (near real-time)
 *   session:token  24 hr   — session tokens
 */
@Slf4j
@Configuration
@EnableCaching
public class RedisCacheConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.afterPropertiesSet();
        return template;
    }

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10))
                .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()))
                .disableCachingNullValues();

        Map<String, RedisCacheConfiguration> cacheConfigs = new HashMap<>();
        cacheConfigs.put("cert:list", defaultConfig.entryTtl(Duration.ofMinutes(5)));
        cacheConfigs.put("cert:detail", defaultConfig.entryTtl(Duration.ofMinutes(30)));
        cacheConfigs.put("standard:list", defaultConfig.entryTtl(Duration.ofMinutes(10)));
        cacheConfigs.put("standard:detail", defaultConfig.entryTtl(Duration.ofHours(1)));
        cacheConfigs.put("developer:profile", defaultConfig.entryTtl(Duration.ofMinutes(15)));
        cacheConfigs.put("lab:equipment", defaultConfig.entryTtl(Duration.ofMinutes(5)));
        cacheConfigs.put("audit:log", defaultConfig.entryTtl(Duration.ofMinutes(2)));
        cacheConfigs.put("session:token", defaultConfig.entryTtl(Duration.ofHours(24)));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(cacheConfigs)
                .build();
    }
}
