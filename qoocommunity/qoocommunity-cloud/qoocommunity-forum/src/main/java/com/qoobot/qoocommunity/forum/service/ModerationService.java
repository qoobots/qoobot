package com.qoobot.qoocommunity.forum.service;

import com.qoobot.qoocommunity.common.exception.QooCommunityException;
import com.qoobot.qoocommunity.forum.domain.Topic;
import com.qoobot.qoocommunity.forum.repository.TopicRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * 内容审核服务。处理敏感词过滤、垃圾检测等。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ModerationService {

    private final TopicRepository topicRepository;

    // 简易敏感词列表（生产环境应接入专业审核服务）
    private static final Set<String> SENSITIVE_WORDS = new HashSet<>(Arrays.asList(
            // placeholder - 实际词库应从配置文件加载
    ));

    /**
     * 检查内容是否包含敏感词
     */
    public boolean containsSensitiveWords(String content) {
        if (content == null) return false;
        String lowerContent = content.toLowerCase();
        return SENSITIVE_WORDS.stream().anyMatch(lowerContent::contains);
    }

    /**
     * 过滤敏感词（替换为 ***）
     */
    public String filterSensitiveWords(String content) {
        if (content == null) return null;
        String result = content;
        for (String word : SENSITIVE_WORDS) {
            result = result.replaceAll("(?i)" + word, "***");
        }
        return result;
    }

    /**
     * 置顶/取消置顶帖子
     */
    @Transactional
    public void togglePin(Long topicId, boolean pinned) {
        Topic topic = topicRepository.findById(topicId)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found"));
        topic.setIsPinned(pinned);
        topicRepository.save(topic);
    }

    /**
     * 锁定/解锁帖子
     */
    @Transactional
    public void toggleLock(Long topicId, boolean locked) {
        Topic topic = topicRepository.findById(topicId)
                .orElseThrow(() -> QooCommunityException.notFound("Topic not found"));
        topic.setIsLocked(locked);
        topicRepository.save(topic);
    }

    /**
     * 验证内容合法性，抛出异常如果不合法
     */
    public void validateContent(String title, String content) {
        if (title != null && (title.length() < 2 || title.length() > 500)) {
            throw QooCommunityException.badRequest("Title must be between 2 and 500 characters");
        }
        if (content != null && containsSensitiveWords(content)) {
            throw QooCommunityException.badRequest("Content contains inappropriate words");
        }
    }
}
