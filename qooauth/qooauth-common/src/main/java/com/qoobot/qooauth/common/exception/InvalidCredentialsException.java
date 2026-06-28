package com.qoobot.qooauth.common.exception;

import com.qoobot.qooauth.common.constants.ErrorCodes;

public class InvalidCredentialsException extends AuthException {

    public InvalidCredentialsException() {
        super(ErrorCodes.INVALID_CREDENTIALS, "Invalid email or password");
    }

    public InvalidCredentialsException(String message) {
        super(ErrorCodes.INVALID_CREDENTIALS, message);
    }
}
