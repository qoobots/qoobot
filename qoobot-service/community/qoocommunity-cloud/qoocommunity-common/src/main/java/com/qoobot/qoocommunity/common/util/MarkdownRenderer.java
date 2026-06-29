package com.qoobot.qoocommunity.common.util;

import org.commonmark.node.*;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;

/**
 * Markdown 到 HTML 渲染器。
 * 用于论坛帖子、Q&A 内容、博客等 Markdown 转 HTML。
 */
public class MarkdownRenderer {

    private static final Parser PARSER = Parser.builder().build();
    private static final HtmlRenderer RENDERER = HtmlRenderer.builder()
            .escapeHtml(true)
            .sanitizeUrls(true)
            .build();

    private MarkdownRenderer() {}

    /**
     * 将 Markdown 渲染为安全 HTML
     */
    public static String render(String markdown) {
        if (markdown == null || markdown.isEmpty()) {
            return "";
        }
        Node document = PARSER.parse(markdown);
        return RENDERER.render(document);
    }

    /**
     * 提取纯文本（去除 Markdown 标记）
     */
    public static String extractText(String markdown) {
        if (markdown == null || markdown.isEmpty()) {
            return "";
        }
        // 简单实现：去除常见 Markdown 标记
        return markdown
                .replaceAll("#+\\s+", "")
                .replaceAll("\\*\\*([^*]+)\\*\\*", "$1")
                .replaceAll("\\*([^*]+)\\*", "$1")
                .replaceAll("`([^`]+)`", "$1")
                .replaceAll("\\[([^\\]]+)\\]\\([^)]+\\)", "$1")
                .replaceAll("!\\[([^\\]]*)\\]\\([^)]+\\)", "$1")
                .replaceAll("[>\\-*+~|]", "")
                .trim();
    }

    /**
     * 生成内容摘要（截取前 maxLength 个字符的纯文本）
     */
    public static String generateSummary(String markdown, int maxLength) {
        String text = extractText(markdown);
        if (text.length() <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength).trim() + "...";
    }
}
