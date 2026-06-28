package com.qoobot.qooauth.common.constants;

/**
 * Unified error codes for all qooauth services.
 */
public final class ErrorCodes {

    private ErrorCodes() {}

    // === Authentication (AUTH_1xxx) ===
    public static final String INVALID_CREDENTIALS = "AUTH_1001";
    public static final String ACCOUNT_LOCKED = "AUTH_1002";
    public static final String ACCOUNT_DISABLED = "AUTH_1003";
    public static final String EMAIL_NOT_VERIFIED = "AUTH_1004";
    public static final String MFA_REQUIRED = "AUTH_1005";
    public static final String MFA_INVALID_CODE = "AUTH_1006";
    public static final String MFA_ALREADY_ENABLED = "AUTH_1011";
    public static final String MFA_METHOD_NOT_FOUND = "AUTH_1012";
    public static final String TOKEN_EXPIRED = "AUTH_1007";
    public static final String TOKEN_INVALID = "AUTH_1008";
    public static final String TOKEN_REVOKED = "AUTH_1009";
    public static final String REFRESH_TOKEN_INVALID = "AUTH_1010";

    // === Registration (REG_2xxx) ===
    public static final String EMAIL_ALREADY_EXISTS = "REG_2001";
    public static final String PHONE_ALREADY_EXISTS = "REG_2002";
    public static final String INVALID_EMAIL_FORMAT = "REG_2003";
    public static final String WEAK_PASSWORD = "REG_2004";
    public static final String NICKNAME_TOO_LONG = "REG_2005";
    public static final String TOS_NOT_ACCEPTED = "REG_2006";
    public static final String PASSWORD_REUSED = "REG_2007";
    public static final String PASSWORD_SAME_AS_CURRENT = "REG_2008";

    // === Rate Limiting (RATE_3xxx) ===
    public static final String RATE_LIMITED = "RATE_3001";
    public static final String TOO_MANY_LOGIN_ATTEMPTS = "RATE_3002";

    // === Authorization (AUTHZ_4xxx) ===
    public static final String INSUFFICIENT_PERMISSIONS = "AUTHZ_4001";
    public static final String INVALID_API_KEY = "AUTHZ_4002";
    public static final String API_KEY_EXPIRED = "AUTHZ_4003";
    public static final String API_KEY_REVOKED = "AUTHZ_4004";
    public static final String API_KEY_LIMIT_EXCEEDED = "AUTHZ_4005";
    public static final String API_KEY_QUOTA_EXCEEDED = "AUTHZ_4006";
    public static final String API_KEY_ALREADY_REVOKED = "AUTHZ_4007";

    // === OAuth (OAUTH_5xxx) ===
    public static final String OAUTH_INVALID_CLIENT = "OAUTH_5001";
    public static final String OAUTH_INVALID_GRANT = "OAUTH_5002";
    public static final String OAUTH_INVALID_REDIRECT_URI = "OAUTH_5003";
    public static final String OAUTH_UNSUPPORTED_GRANT_TYPE = "OAUTH_5004";
    public static final String OAUTH_INVALID_CODE = "OAUTH_5005";
    public static final String OAUTH_PKCE_REQUIRED = "OAUTH_5006";
    public static final String OAUTH_UNSUPPORTED_RESPONSE_TYPE = "OAUTH_5007";

    // === Device (DEV_6xxx) ===
    public static final String DEVICE_NOT_FOUND = "DEV_6001";
    public static final String DEVICE_ALREADY_BOUND = "DEV_6002";
    public static final String DEVICE_CERT_INVALID = "DEV_6003";
    public static final String DEVICE_FINGERPRINT_MISMATCH = "DEV_6004";
    public static final String DEVICE_NOT_TRUSTED = "DEV_6005";

    // === General (GEN_9xxx) ===
    public static final String INTERNAL_ERROR = "GEN_9001";
    public static final String VALIDATION_ERROR = "GEN_9002";
    public static final String NOT_FOUND = "GEN_9003";
    public static final String BAD_REQUEST = "GEN_9004";
}
