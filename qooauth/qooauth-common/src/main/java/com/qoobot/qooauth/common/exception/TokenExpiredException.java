package com.qoobot.qooauth.common.exception;

import com.qoobot.qooauth.common.constants.ErrorCodes;

public class TokenExpiredException extends AuthException {

    public TokenExpiredException() {
        super(ErrorCodes.TOKEN_EXPIRED, "Token has expired");
    }

    public TokenExpiredException(String message) {
        super(ErrorCodes.TOKEN_EXPIRED, message);
    }
}
