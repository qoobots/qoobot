package com.qoobot.qoogear.common.enums;

public enum CertLevel {
    BASIC("MFQ Basic", "基础兼容认证", 1),
    PREMIUM("MFQ Premium", "深度集成认证", 2),
    PRO("MFQ Pro", "专业级认证", 3);

    private final String displayName;
    private final String description;
    private final int level;

    CertLevel(String displayName, String description, int level) {
        this.displayName = displayName;
        this.description = description;
        this.level = level;
    }

    public String getDisplayName() { return displayName; }
    public String getDescription() { return description; }
    public int getLevel() { return level; }
}
