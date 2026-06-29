package com.qoobot.qoochain.common.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public class QooChainException extends RuntimeException {

    private final HttpStatus status;
    private final String errorCode;

    public QooChainException(HttpStatus status, String errorCode, String message) {
        super(message);
        this.status = status;
        this.errorCode = errorCode;
    }

    public static QooChainException notFound(String resource, String id) {
        return new QooChainException(
            HttpStatus.NOT_FOUND,
            "NOT_FOUND",
            String.format("%s not found: %s", resource, id)
        );
    }

    public static QooChainException badRequest(String message) {
        return new QooChainException(HttpStatus.BAD_REQUEST, "BAD_REQUEST", message);
    }

    public static QooChainException conflict(String message) {
        return new QooChainException(HttpStatus.CONFLICT, "CONFLICT", message);
    }

    public static QooChainException forbidden(String message) {
        return new QooChainException(HttpStatus.FORBIDDEN, "FORBIDDEN", message);
    }
}
