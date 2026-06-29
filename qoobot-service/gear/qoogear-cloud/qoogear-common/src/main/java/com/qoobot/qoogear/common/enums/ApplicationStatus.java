package com.qoobot.qoogear.common.enums;

public enum ApplicationStatus {
    DRAFT("草稿"),
    SUBMITTED("已提交"),
    COMPLIANCE_CHECK("合规审查中"),
    REVIEWING("审核中"),
    ASSIGNED("已分配实验室"),
    TESTING("测试中"),
    TEST_COMPLETED("测试完成"),
    SECURITY_REVIEW("安全审查中"),
    APPROVED("已批准"),
    REJECTED("已驳回"),
    REVOKED("已吊销"),
    EXPIRED("已过期");

    private final String displayName;

    ApplicationStatus(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() { return displayName; }

    public boolean canTransitionTo(ApplicationStatus target) {
        return switch (this) {
            case DRAFT -> target == SUBMITTED;
            case SUBMITTED -> target == COMPLIANCE_CHECK || target == REJECTED;
            case COMPLIANCE_CHECK -> target == REVIEWING || target == REJECTED;
            case REVIEWING -> target == ASSIGNED || target == REJECTED;
            case ASSIGNED -> target == TESTING || target == REJECTED;
            case TESTING -> target == TEST_COMPLETED;
            case TEST_COMPLETED -> target == SECURITY_REVIEW || target == APPROVED;
            case SECURITY_REVIEW -> target == APPROVED || target == REJECTED;
            case APPROVED -> target == REVOKED || target == EXPIRED;
            case REJECTED, REVOKED, EXPIRED -> false;
        };
    }
}
