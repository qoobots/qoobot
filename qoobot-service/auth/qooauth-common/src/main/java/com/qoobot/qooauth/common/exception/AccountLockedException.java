package com.qoobot.qooauth.common.exception;

import com.qoobot.qooauth.common.constants.ErrorCodes;

import java.time.Instant;

public class AccountLockedException extends AuthException {

    private final Instant lockedUntil;

    public AccountLockedException(Instant lockedUntil) {
        super(ErrorCodes.ACCOUNT_LOCKED, "Account is locked until " + lockedUntil.toString());
        this.lockedUntil = lockedUntil;
    }

    public Instant getLockedUntil() {
        return lockedUntil;
    }
}
