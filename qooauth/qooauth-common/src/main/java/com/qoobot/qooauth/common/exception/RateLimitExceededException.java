package com.qoobot.qooauth.common.exception;

import com.qoobot.qooauth.common.constants.ErrorCodes;

public class RateLimitExceededException extends AuthException {

    private final long retryAfterSeconds;

    public RateLimitExceededException(long retryAfterSeconds) {
        super(ErrorCodes.RATE_LIMITED, "Rate limit exceeded. Retry after " + retryAfterSeconds + " seconds");
        this.retryAfterSeconds = retryAfterSeconds;
    }

    public long getRetryAfterSeconds() {
        return retryAfterSeconds;
    }
}
