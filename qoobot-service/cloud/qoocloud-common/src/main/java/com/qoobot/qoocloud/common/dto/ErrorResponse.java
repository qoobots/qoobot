package com.qoobot.qoocloud.common.dto;

import java.time.Instant;

/**
 * Standard error response body.
 */
public class ErrorResponse {

    private int status;
    private String error;
    private String errorCode;
    private String message;
    private String path;
    private Instant timestamp;

    public ErrorResponse() {
        this.timestamp = Instant.now();
    }

    public ErrorResponse(int status, String errorCode, String message, String path) {
        this();
        this.status = status;
        this.errorCode = errorCode;
        this.message = message;
        this.path = path;
    }

    // Getters and setters
    public int getStatus() { return status; }
    public void setStatus(int status) { this.status = status; }
    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
    public String getErrorCode() { return errorCode; }
    public void setErrorCode(String errorCode) { this.errorCode = errorCode; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getPath() { return path; }
    public void setPath(String path) { this.path = path; }
    public Instant getTimestamp() { return timestamp; }
    public void setTimestamp(Instant timestamp) { this.timestamp = timestamp; }
}
