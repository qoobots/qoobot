package com.qoobot.qoocommunity.content.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

/**
 * 品牌资产管理服务。
 * 提供 Logo、字体、配色规范等品牌资产信息。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BrandAssetService {

    /**
     * 获取品牌资产信息
     */
    public Map<String, Object> getBrandAssets() {
        Map<String, Object> assets = new HashMap<>();

        // Logo 信息
        Map<String, String> logo = new HashMap<>();
        logo.put("primary", "/brand/logo/qoobot-logo-primary.svg");
        logo.put("white", "/brand/logo/qoobot-logo-white.svg");
        logo.put("icon", "/brand/logo/qoobot-icon.svg");
        assets.put("logo", logo);

        // 配色方案
        Map<String, String> colors = new HashMap<>();
        colors.put("primary", "#4A90D9");
        colors.put("secondary", "#34C759");
        colors.put("accent", "#FF6B35");
        colors.put("background", "#F8F9FA");
        colors.put("text", "#1A1A2E");
        colors.put("textSecondary", "#6C757D");
        assets.put("colors", colors);

        // 字体
        Map<String, String> fonts = new HashMap<>();
        fonts.put("heading", "Inter, sans-serif");
        fonts.put("body", "Noto Sans SC, sans-serif");
        fonts.put("mono", "JetBrains Mono, monospace");
        assets.put("fonts", fonts);

        // 品牌指南
        assets.put("brandGuideUrl", "/brand/guidelines.pdf");
        assets.put("mediaKitUrl", "/brand/media-kit.zip");

        return assets;
    }
}
