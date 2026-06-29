package com.qoobot.qooauth.common.constants;

/**
 * Audit action types for comprehensive operation logging.
 */
public final class AuditActions {

    private AuditActions() {}

    // User account actions
    public static final String USER_REGISTER = "USER_REGISTER";
    public static final String USER_LOGIN = "USER_LOGIN";
    public static final String USER_LOGOUT = "USER_LOGOUT";
    public static final String USER_MFA_VERIFY = "USER_MFA_VERIFY";
    public static final String USER_MFA_ENABLE = "USER_MFA_ENABLE";
    public static final String USER_MFA_DISABLE = "USER_MFA_DISABLE";
    public static final String USER_PASSWORD_CHANGE = "USER_PASSWORD_CHANGE";
    public static final String USER_PROFILE_UPDATE = "USER_PROFILE_UPDATE";
    public static final String USER_ACCOUNT_RECOVERY = "USER_ACCOUNT_RECOVERY";
    public static final String USER_ACCOUNT_DELETE = "USER_ACCOUNT_DELETE";

    // Token actions
    public static final String TOKEN_ISSUE = "TOKEN_ISSUE";
    public static final String TOKEN_REFRESH = "TOKEN_REFRESH";
    public static final String TOKEN_REVOKE = "TOKEN_REVOKE";
    public static final String TOKEN_VERIFY = "TOKEN_VERIFY";

    // OAuth actions
    public static final String OAUTH_AUTHORIZE = "OAUTH_AUTHORIZE";
    public static final String OAUTH_TOKEN_GRANT = "OAUTH_TOKEN_GRANT";
    public static final String OAUTH_CONSENT = "OAUTH_CONSENT";

    // Device actions
    public static final String DEVICE_ACTIVATE = "DEVICE_ACTIVATE";
    public static final String DEVICE_BIND = "DEVICE_BIND";
    public static final String DEVICE_UNBIND = "DEVICE_UNBIND";
    public static final String DEVICE_LOCK = "DEVICE_LOCK";
    public static final String DEVICE_WIPE = "DEVICE_WIPE";
    public static final String DEVICE_CERT_ISSUE = "DEVICE_CERT_ISSUE";
    public static final String DEVICE_CERT_REVOKE = "DEVICE_CERT_REVOKE";

    // API Key actions
    public static final String API_KEY_CREATE = "API_KEY_CREATE";
    public static final String API_KEY_REVOKE = "API_KEY_REVOKE";

    // Admin actions
    public static final String ADMIN_USER_SUSPEND = "ADMIN_USER_SUSPEND";
    public static final String ADMIN_USER_RESTORE = "ADMIN_USER_RESTORE";
    public static final String ADMIN_DEVICE_LOCK = "ADMIN_DEVICE_LOCK";
    public static final String ADMIN_CONFIG_CHANGE = "ADMIN_CONFIG_CHANGE";
}
