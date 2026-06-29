package com.qoobot.qooauth.auth.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.qoobot.qooauth.auth.service.AuthService.UserInfo;
import com.qoobot.qooauth.auth.service.TokenService.TokenPair;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record TokenResponse(
        String accessToken,
        String refreshToken,
        String idToken,
        String tokenType,
        long expiresIn,
        UserInfo user,
        Boolean requiresMfa,
        String mfaToken,
        String[] availableMethods
) {
    public static TokenResponse fromTokenPair(TokenPair tokens, UserInfo user) {
        return new TokenResponse(
                tokens.accessToken(), tokens.refreshToken(), tokens.idToken(),
                tokens.tokenType(), tokens.expiresIn(),
                user, false, null, null
        );
    }

    public static TokenResponse mfaRequired(String mfaToken, String[] methods) {
        return new TokenResponse(
                null, null, null, null, 0,
                null, true, mfaToken, methods
        );
    }
}
