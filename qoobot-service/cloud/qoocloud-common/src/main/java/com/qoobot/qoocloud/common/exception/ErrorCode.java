package com.qoobot.qoocloud.common.exception;

/**
 * Centralized error code registry.
 */
public enum ErrorCode {

    // General
    INVALID_REQUEST(400, "INVALID_REQUEST"),
    UNAUTHORIZED(401, "UNAUTHORIZED"),
    FORBIDDEN(403, "FORBIDDEN"),
    NOT_FOUND(404, "NOT_FOUND"),
    CONFLICT(409, "CONFLICT"),
    RATE_LIMITED(429, "RATE_LIMITED"),
    INTERNAL_ERROR(500, "INTERNAL_ERROR"),
    SERVICE_UNAVAILABLE(503, "SERVICE_UNAVAILABLE"),

    // Device
    DEVICE_NOT_FOUND(404, "DEVICE_NOT_FOUND"),
    DEVICE_NOT_ACTIVATED(403, "DEVICE_NOT_ACTIVATED"),
    DEVICE_ALREADY_REGISTERED(409, "DEVICE_ALREADY_REGISTERED"),

    // Inference
    MODEL_NOT_FOUND(404, "MODEL_NOT_FOUND"),
    INFERENCE_FAILED(500, "INFERENCE_FAILED"),
    GPU_UNAVAILABLE(503, "GPU_UNAVAILABLE"),
    GPU_QUEUE_FULL(429, "GPU_QUEUE_FULL"),

    // OTA
    OTA_IN_PROGRESS(409, "OTA_IN_PROGRESS"),
    OTA_ROLLBACK_FAILED(500, "OTA_ROLLBACK_FAILED"),
    OTA_PACKAGE_NOT_FOUND(404, "OTA_PACKAGE_NOT_FOUND"),

    // Service
    SERVICE_DEGRADED(503, "SERVICE_DEGRADED");

    private final int httpStatus;
    private final String code;

    ErrorCode(int httpStatus, String code) {
        this.httpStatus = httpStatus;
        this.code = code;
    }

    public int getHttpStatus() { return httpStatus; }
    public String getCode() { return code; }
}
