package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.service.TokenService.TokenPair;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AccountLockedException;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.exception.InvalidCredentialsException;
import com.qoobot.qooauth.common.util.IdGenerator;
import com.qoobot.qooauth.auth.entity.User;
import com.qoobot.qooauth.auth.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;

/**
 * Core authentication service.
 * Handles user registration, login, token management, and session lifecycle.
 */
@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordService passwordService;
    private final TokenService tokenService;
    private final SessionService sessionService;
    private final RateLimitService rateLimitService;

    public AuthService(UserRepository userRepository,
                       PasswordService passwordService,
                       TokenService tokenService,
                       SessionService sessionService,
                       RateLimitService rateLimitService) {
        this.userRepository = userRepository;
        this.passwordService = passwordService;
        this.tokenService = tokenService;
        this.sessionService = sessionService;
        this.rateLimitService = rateLimitService;
    }

    /**
     * Register a new QooBot ID account.
     */
    @Transactional
    public RegisterResult register(String email, String password, String nickname,
                                    String language, boolean acceptTos) {
        // Validate email format
        if (!isValidEmail(email)) {
            throw new AuthException(ErrorCodes.INVALID_EMAIL_FORMAT, "Invalid email format");
        }

        // Check email uniqueness
        if (userRepository.findByEmail(email.toLowerCase()).isPresent()) {
            throw new AuthException(ErrorCodes.EMAIL_ALREADY_EXISTS, "Email already registered");
        }

        // Validate password strength
        if (!isStrongPassword(password)) {
            throw new AuthException(ErrorCodes.WEAK_PASSWORD,
                    "Password must be at least 8 characters with upper, lower, digit, and special character");
        }

        // Validate nickname length
        if (nickname.length() > 64) {
            throw new AuthException(ErrorCodes.NICKNAME_TOO_LONG,
                    "Nickname must be 64 characters or fewer");
        }

        // Hash password
        String passwordHash = passwordService.hash(password);
        String salt = passwordService.generateSalt();

        // Create user
        User user = new User();
        user.setUserId(IdGenerator.generateUserId());
        user.setEmail(email.toLowerCase());
        user.setPasswordHash(passwordHash);
        user.setPasswordSalt(salt);
        user.setNickname(nickname);
        user.setLanguage(language != null ? language : "zh-CN");
        user.setState("EMAIL_VERIFICATION_PENDING");
        user.setCreatedAt(Instant.now());
        user.setUpdatedAt(Instant.now());

        user = userRepository.save(user);

        return new RegisterResult(user.getUserId(), user.getEmail(), user.getState());
    }

    /**
     * Authenticate a user with email and password.
     * Returns token pair on success.
     */
    @Transactional
    public LoginResult login(String email, String password, String deviceId,
                              String clientId, String ip, String userAgent) {
        // Rate limit check
        rateLimitService.checkLoginRateLimit(email);

        // Find user
        User user = userRepository.findByEmail(email.toLowerCase())
                .orElseThrow(() -> {
                    rateLimitService.recordLoginFailure(email);
                    return new InvalidCredentialsException();
                });

        // Check account state
        if ("LOCKED".equals(user.getState())) {
            throw new AccountLockedException(user.getUpdatedAt().plus(15, ChronoUnit.MINUTES));
        }
        if ("SUSPENDED".equals(user.getState())) {
            throw new AuthException(ErrorCodes.ACCOUNT_DISABLED, "Account has been suspended");
        }
        if ("DELETED".equals(user.getState())) {
            throw new InvalidCredentialsException();
        }

        // Verify password
        if (!passwordService.verify(user.getPasswordHash(), password)) {
            rateLimitService.recordLoginFailure(email);
            throw new InvalidCredentialsException();
        }

        // Check if MFA is required
        if (user.isMfaEnabled()) {
            // Create MFA session token
            String mfaToken = tokenService.issueTokens(
                    user.getUserId(), user.getEmail(),
                    user.getNickname(), getAvatarUrl(user),
                    "mfa_pending").accessToken();
            return LoginResult.mfaRequired(mfaToken, user.getMfaMethods());
        }

        // Clear rate limit on success
        rateLimitService.clearLoginFailures(email);

        // Update last login
        user.setLastLoginAt(Instant.now());
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        // Create session
        String sessionId = sessionService.createSession(
                user.getUserId(), deviceId, clientId, ip, userAgent);

        // Issue tokens
        TokenPair tokens = tokenService.issueTokens(
                user.getUserId(), user.getEmail(),
                user.getNickname(), getAvatarUrl(user),
                "openid profile email");

        return LoginResult.success(tokens, toUserInfo(user));
    }

    /**
     * Logout user: revoke tokens and session.
     */
    public void logout(String userId, String accessToken, String refreshToken, boolean logoutAllDevices) {
        if (logoutAllDevices) {
            sessionService.revokeAllSessions(userId);
        }
        tokenService.revokeTokens(accessToken, refreshToken);
    }

    /**
     * Refresh an access token using a refresh token.
     */
    public TokenPair refreshToken(String refreshToken, String email, String nickname,
                                   String avatarUrl) {
        return tokenService.refreshTokens(refreshToken, email, nickname, avatarUrl, "openid profile email");
    }

    // --- Private helpers ---

    private boolean isValidEmail(String email) {
        return email != null && email.matches("^[\\w.+-]+@[\\w-]+\\.[\\w.-]+$");
    }

    private boolean isStrongPassword(String password) {
        if (password == null || password.length() < 8) return false;
        boolean hasUpper = false, hasLower = false, hasDigit = false, hasSpecial = false;
        for (char c : password.toCharArray()) {
            if (Character.isUpperCase(c)) hasUpper = true;
            else if (Character.isLowerCase(c)) hasLower = true;
            else if (Character.isDigit(c)) hasDigit = true;
            else hasSpecial = true;
        }
        return hasUpper && hasLower && hasDigit && hasSpecial;
    }

    private String getAvatarUrl(User user) {
        return user.getAvatarHash() != null
                ? "https://cdn.qoobot.com/avatars/" + user.getAvatarHash()
                : null;
    }

    private UserInfo toUserInfo(User user) {
        return new UserInfo(
                user.getUserId(), user.getEmail(), user.getNickname(),
                getAvatarUrl(user), user.isEmailVerified()
        );
    }

    // --- DTOs ---

    public record RegisterResult(String userId, String email, String state) {}

    public record LoginResult(
            TokenPair tokens,
            UserInfo user,
            boolean requiresMfa,
            String mfaToken,
            String[] mfaMethods
    ) {
        public static LoginResult success(TokenPair tokens, UserInfo user) {
            return new LoginResult(tokens, user, false, null, null);
        }

        public static LoginResult mfaRequired(String mfaToken, String[] methods) {
            return new LoginResult(null, null, true, mfaToken, methods);
        }
    }

    public record UserInfo(
            String sub, String email, String nickname,
            String avatarUrl, boolean emailVerified
    ) {}
}
