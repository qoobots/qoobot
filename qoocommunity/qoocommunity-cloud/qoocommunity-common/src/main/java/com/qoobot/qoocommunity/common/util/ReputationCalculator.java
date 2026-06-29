package com.qoobot.qoocommunity.common.util;

/**
 * 社区声望计算器。
 * 根据用户社区行为计算声望值。
 */
public class ReputationCalculator {

    private ReputationCalculator() {}

    // 声望分值常量
    public static final int QUESTION_UPVOTE = 5;
    public static final int ANSWER_UPVOTE = 10;
    public static final int ANSWER_ACCEPTED = 15;
    public static final int ANSWER_DOWNVOTE = -2;
    public static final int QUESTION_DOWNVOTE = -2;
    public static final int TOPIC_CREATED = 2;
    public static final int REPLY_CREATED = 1;
    public static final int PR_MERGED = 20;
    public static final int PR_REVIEWED = 5;
    public static final int BLOG_PUBLISHED = 10;
    public static final int SHOWCASE_APPROVED = 8;

    /**
     * 计算新声望值
     */
    public static int calculateDelta(String actionType) {
        return switch (actionType.toUpperCase()) {
            case "QUESTION_UPVOTE" -> QUESTION_UPVOTE;
            case "ANSWER_UPVOTE" -> ANSWER_UPVOTE;
            case "ANSWER_ACCEPTED" -> ANSWER_ACCEPTED;
            case "ANSWER_DOWNVOTE" -> ANSWER_DOWNVOTE;
            case "QUESTION_DOWNVOTE" -> QUESTION_DOWNVOTE;
            case "TOPIC_CREATED" -> TOPIC_CREATED;
            case "REPLY_CREATED" -> REPLY_CREATED;
            case "PR_MERGED" -> PR_MERGED;
            case "PR_REVIEWED" -> PR_REVIEWED;
            case "BLOG_PUBLISHED" -> BLOG_PUBLISHED;
            case "SHOWCASE_APPROVED" -> SHOWCASE_APPROVED;
            default -> 0;
        };
    }

    /**
     * 根据声望值计算等级
     */
    public static String getLevel(int reputation) {
        if (reputation >= 10000) return "LEGEND";
        if (reputation >= 5000) return "MASTER";
        if (reputation >= 2000) return "EXPERT";
        if (reputation >= 500) return "ADVANCED";
        if (reputation >= 100) return "INTERMEDIATE";
        if (reputation >= 10) return "BEGINNER";
        return "NEWCOMER";
    }

    /**
     * 根据贡献者等级名称计算等级值（用于排序）
     */
    public static int getLevelWeight(String level) {
        return switch (level.toUpperCase()) {
            case "TSC" -> 6;
            case "COMMITTER" -> 5;
            case "MAINTAINER" -> 4;
            case "CONTRIBUTOR" -> 3;
            default -> 0;
        };
    }
}
