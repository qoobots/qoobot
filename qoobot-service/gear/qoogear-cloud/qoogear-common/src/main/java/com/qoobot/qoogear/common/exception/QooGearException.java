package com.qoobot.qoogear.common.exception;

/**
 * Base business exception for QooGear module.
 */
public class QooGearException extends RuntimeException {

    private final int errorCode;

    public QooGearException(int errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public QooGearException(int errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public int getErrorCode() {
        return errorCode;
    }

    // Common error factories
    public static QooGearException notFound(String resource, Object id) {
        return new QooGearException(404, resource + " not found: " + id);
    }

    public static QooGearException badRequest(String message) {
        return new QooGearException(400, message);
    }

    public static QooGearException forbidden(String message) {
        return new QooGearException(403, message);
    }

    public static QooGearException conflict(String message) {
        return new QooGearException(409, message);
    }
}
