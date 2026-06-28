package com.qoobot.qoocommunity.common.exception;

import lombok.Getter;

@Getter
public class QooCommunityException extends RuntimeException {

    private final int code;

    public QooCommunityException(int code, String message) {
        super(message);
        this.code = code;
    }

    public QooCommunityException(String message) {
        super(message);
        this.code = 500;
    }

    public static QooCommunityException notFound(String message) {
        return new QooCommunityException(404, message);
    }

    public static QooCommunityException badRequest(String message) {
        return new QooCommunityException(400, message);
    }

    public static QooCommunityException forbidden(String message) {
        return new QooCommunityException(403, message);
    }

    public static QooCommunityException unauthorized() {
        return new QooCommunityException(401, "Unauthorized");
    }
}
