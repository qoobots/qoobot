package com.qoobot.qoogear.common.enums;

public enum TestResult {
    PASS("通过"),
    FAIL("未通过"),
    CONDITIONAL_PASS("条件通过");

    private final String displayName;

    TestResult(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() { return displayName; }
}
