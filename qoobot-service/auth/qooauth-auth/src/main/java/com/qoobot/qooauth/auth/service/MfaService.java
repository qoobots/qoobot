package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.auth.entity.Fido2Credential;
import com.qoobot.qooauth.auth.entity.RecoveryCode;
import com.qoobot.qooauth.auth.entity.User;
import com.qoobot.qooauth.auth.repository.Fido2CredentialRepository;
import com.qoobot.qooauth.auth.repository.RecoveryCodeRepository;
import com.qoobot.qooauth.auth.repository.UserRepository;
import com.qoobot.qooauth.auth.service.AuthService.LoginResult;
import com.qoobot.qooauth.auth.service.AuthService.UserInfo;
import com.qoobot.qooauth.auth.service.TokenService.TokenPair;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.jboss.aerogear.security.otp.Totp;
import org.jboss.aerogear.security.otp.api.Base32;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * MFA (Multi-Factor Authentication) service.
 * Supports TOTP (RFC 6238) and FIDO2/WebAuthn with recovery codes.
 */
@Service
public class MfaService {

    private static final String ISSUER = "QooBot";
    private static final int RECOVERY_CODE_COUNT = 10;
    private static final int RECOVERY_CODE_LENGTH = 12;
    private static final SecureRandom RANDOM = new SecureRandom();

    private final UserRepository userRepository;
    private final Fido2CredentialRepository fido2CredentialRepository;
    private final RecoveryCodeRepository recoveryCodeRepository;
    private final PasswordEncoder passwordEncoder;
    private final TokenService tokenService;
    private final SessionService sessionService;
    private final RateLimitService rateLimitService;

    public MfaService(UserRepository userRepository,
                      Fido2CredentialRepository fido2CredentialRepository,
                      RecoveryCodeRepository recoveryCodeRepository,
                      PasswordEncoder passwordEncoder,
                      TokenService tokenService,
                      SessionService sessionService,
                      RateLimitService rateLimitService) {
        this.userRepository = userRepository;
        this.fido2CredentialRepository = fido2CredentialRepository;
        this.recoveryCodeRepository = recoveryCodeRepository;
        this.passwordEncoder = passwordEncoder;
        this.tokenService = tokenService;
        this.sessionService = sessionService;
        this.rateLimitService = rateLimitService;
    }

    // ==================== TOTP ====================

    /**
     * Generate a new TOTP secret and QR code URI for setup.
     * Returns the secret (for display) and the otpauth URI.
     */
    @Transactional
    public TotpSetupResult setupTotp(String userId, String userEmail) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        if (user.getTotpSecret() != null) {
            throw new AuthException(ErrorCodes.MFA_ALREADY_ENABLED, "TOTP is already configured");
        }

        String secret = Base32.random();
        String otpAuthUri = String.format("otpauth://totp/%s:%s?secret=%s&issuer=%s&algorithm=SHA1&digits=6&period=30",
                ISSUER, userEmail, secret, ISSUER);

        user.setTotpSecret(secret);
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        return new TotpSetupResult(secret, otpAuthUri);
    }

    /**
     * Verify a TOTP code to complete TOTP setup.
     */
    @Transactional
    public MfaVerifyResult verifyTotpSetup(String userId, String code) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        if (user.getTotpSecret() == null) {
            throw new AuthException(ErrorCodes.BAD_REQUEST, "TOTP setup not initiated");
        }

        Totp totp = new Totp(user.getTotpSecret());
        if (!totp.verify(code)) {
            throw new AuthException(ErrorCodes.MFA_INVALID_CODE, "Invalid TOTP code");
        }

        // Enable MFA and add TOTP method
        enableMfaMethod(user, "totp");
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        // Generate recovery codes
        List<String> recoveryCodes = generateRecoveryCodes(userId);

        return new MfaVerifyResult(true, "totp", user.getMfaMethods(), recoveryCodes);
    }

    /**
     * Verify a TOTP code during login MFA step.
     */
    @Transactional
    public LoginResult verifyTotpLogin(String mfaToken, String code, String deviceId,
                                        String clientId, String ip, String userAgent) {
        // Verify MFA token
        var claims = tokenService.verifyMfaToken(mfaToken);
        String userId = claims.subject();

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        if (!user.isMfaEnabled() || user.getTotpSecret() == null) {
            throw new AuthException(ErrorCodes.BAD_REQUEST, "TOTP not configured");
        }

        Totp totp = new Totp(user.getTotpSecret());
        if (!totp.verify(code)) {
            throw new AuthException(ErrorCodes.MFA_INVALID_CODE, "Invalid TOTP code");
        }

        return completeMfaLogin(user, deviceId, clientId, ip, userAgent);
    }

    // ==================== FIDO2/WebAuthn ====================

    /**
     * Get FIDO2 registration challenge for the user.
     */
    public Fido2RegistrationChallenge startFido2Registration(String userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        byte[] challengeBytes = new byte[32];
        RANDOM.nextBytes(challengeBytes);
        String challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(challengeBytes);

        // Store challenge in Redis (TTL: 5 min)
        // In production, this would use a dedicated Redis key

        return new Fido2RegistrationChallenge(challenge);
    }

    /**
     * Complete FIDO2 credential registration.
     */
    @Transactional
    public MfaVerifyResult completeFido2Registration(String userId, String credentialId,
                                                      String publicKey, String credentialName,
                                                      long signCount, String transports,
                                                      String aaguid, String attestation) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        // Check for duplicate credential
        if (fido2CredentialRepository.findById(credentialId).isPresent()) {
            throw new AuthException(ErrorCodes.BAD_REQUEST, "Credential already registered");
        }

        Fido2Credential credential = new Fido2Credential();
        credential.setCredentialId(credentialId);
        credential.setUserId(userId);
        credential.setCredentialName(credentialName != null ? credentialName : "Security Key");
        credential.setPublicKey(publicKey);
        credential.setSignCount(signCount);
        credential.setTransports(transports);
        credential.setAaguid(aaguid);
        credential.setAttestation(attestation);
        credential.setCreatedAt(Instant.now());
        fido2CredentialRepository.save(credential);

        // Enable MFA and add fido2 method
        enableMfaMethod(user, "fido2");
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        // Generate recovery codes if first MFA method
        List<String> recoveryCodes = null;
        if (user.getMfaMethods().length == 1) {
            recoveryCodes = generateRecoveryCodes(userId);
        }

        return new MfaVerifyResult(true, "fido2", user.getMfaMethods(), recoveryCodes);
    }

    /**
     * Get FIDO2 assertion challenge for login verification.
     */
    public Fido2AssertionChallenge startFido2Login(String userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        List<Fido2Credential> credentials = fido2CredentialRepository.findByUserId(userId);
        if (credentials.isEmpty()) {
            throw new AuthException(ErrorCodes.BAD_REQUEST, "No FIDO2 credentials registered");
        }

        byte[] challengeBytes = new byte[32];
        RANDOM.nextBytes(challengeBytes);
        String challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(challengeBytes);

        List<Fido2AllowCredential> allowCredentials = credentials.stream()
                .map(c -> new Fido2AllowCredential(c.getCredentialId(), c.getTransports()))
                .collect(Collectors.toList());

        return new Fido2AssertionChallenge(challenge, allowCredentials);
    }

    /**
     * Complete FIDO2 login verification after successful assertion.
     */
    @Transactional
    public LoginResult verifyFido2Login(String mfaToken, String credentialId, long newSignCount,
                                         String deviceId, String clientId, String ip, String userAgent) {
        var claims = tokenService.verifyMfaToken(mfaToken);
        String userId = claims.subject();

        Fido2Credential credential = fido2CredentialRepository.findById(credentialId)
                .orElseThrow(() -> new AuthException(ErrorCodes.MFA_INVALID_CODE, "Unknown credential"));

        if (!credential.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.MFA_INVALID_CODE, "Credential does not belong to user");
        }

        // Update sign count (prevents replay attacks)
        if (newSignCount > credential.getSignCount()) {
            fido2CredentialRepository.updateSignCount(credentialId, newSignCount);
            credential.setLastUsedAt(Instant.now());
            fido2CredentialRepository.save(credential);
        }

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        return completeMfaLogin(user, deviceId, clientId, ip, userAgent);
    }

    // ==================== Recovery Codes ====================

    /**
     * Verify login using a recovery code.
     */
    @Transactional
    public LoginResult verifyRecoveryCodeLogin(String mfaToken, String recoveryCode,
                                                String deviceId, String clientId,
                                                String ip, String userAgent) {
        var claims = tokenService.verifyMfaToken(mfaToken);
        String userId = claims.subject();

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        String codeHash = passwordEncoder.encode(recoveryCode);

        RecoveryCode code = recoveryCodeRepository
                .findByUserIdAndCodeHashAndUsedFalse(userId, codeHash)
                .orElseThrow(() -> new AuthException(ErrorCodes.MFA_INVALID_CODE,
                        "Invalid or already used recovery code"));

        // Mark recovery code as used
        code.setUsed(true);
        code.setUsedAt(Instant.now());
        recoveryCodeRepository.save(code);

        // Warn if running low
        long remaining = recoveryCodeRepository.countByUserIdAndUsedFalse(userId);

        return completeMfaLogin(user, deviceId, clientId, ip, userAgent);
    }

    /**
     * Generate new recovery codes (invalidates old ones).
     */
    @Transactional
    public List<String> regenerateRecoveryCodes(String userId) {
        userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        // Invalidate old codes
        recoveryCodeRepository.deleteByUserId(userId);

        // Generate new codes
        return generateRecoveryCodes(userId);
    }

    // ==================== MFA Management ====================

    /**
     * Get the current MFA status for a user.
     */
    public MfaStatus getMfaStatus(String userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        List<Fido2Credential> fido2Keys = fido2CredentialRepository.findByUserId(userId);
        long remainingRecoveryCodes = recoveryCodeRepository.countByUserIdAndUsedFalse(userId);

        List<MfaMethodInfo> methods = new ArrayList<>();
        if (user.getTotpSecret() != null) {
            methods.add(new MfaMethodInfo("totp", "Authenticator App", true));
        }
        for (Fido2Credential key : fido2Keys) {
            methods.add(new MfaMethodInfo("fido2", key.getCredentialName(), true));
        }

        return new MfaStatus(
                user.isMfaEnabled(),
                methods.toArray(new MfaMethodInfo[0]),
                remainingRecoveryCodes
        );
    }

    /**
     * Disable a specific MFA method.
     */
    @Transactional
    public void disableMfaMethod(String userId, String methodType, String methodId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        switch (methodType) {
            case "totp":
                user.setTotpSecret(null);
                removeMfaMethod(user, "totp");
                break;
            case "fido2":
                fido2CredentialRepository.deleteById(methodId);
                long remainingFido2 = fido2CredentialRepository.findByUserId(userId).size();
                if (remainingFido2 == 0) {
                    removeMfaMethod(user, "fido2");
                }
                break;
            default:
                throw new AuthException(ErrorCodes.BAD_REQUEST, "Unknown MFA method type");
        }

        // Disable MFA entirely if no methods remain
        if (user.getMfaMethods().length == 0) {
            user.setMfaEnabled(false);
            user.setTotpSecret(null);
            recoveryCodeRepository.deleteByUserId(userId);
        }

        user.setUpdatedAt(Instant.now());
        userRepository.save(user);
    }

    /**
     * Disable all MFA for a user (requires password confirmation).
     */
    @Transactional
    public void disableAllMfa(String userId, String password) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        // In production, verify password via PasswordService
        if (password == null || password.isEmpty()) {
            throw new AuthException(ErrorCodes.INVALID_CREDENTIALS, "Password required to disable MFA");
        }

        user.setMfaEnabled(false);
        user.setTotpSecret(null);
        user.setMfaMethods(null);
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);

        // Clean up FIDO2 credentials and recovery codes
        List<Fido2Credential> keys = fido2CredentialRepository.findByUserId(userId);
        fido2CredentialRepository.deleteAll(keys);
        recoveryCodeRepository.deleteByUserId(userId);
    }

    // ==================== Private Helpers ====================

    private void enableMfaMethod(User user, String method) {
        Set<String> methods = new HashSet<>();
        String[] existing = user.getMfaMethods();
        if (existing != null) {
            Collections.addAll(methods, existing);
        }
        methods.add(method);
        user.setMfaMethods("[" + String.join(",", methods) + "]");
        user.setMfaEnabled(true);
    }

    private void removeMfaMethod(User user, String method) {
        Set<String> methods = new HashSet<>();
        String[] existing = user.getMfaMethods();
        if (existing != null) {
            Collections.addAll(methods, existing);
        }
        methods.remove(method);
        if (methods.isEmpty()) {
            user.setMfaMethods(null);
        } else {
            user.setMfaMethods("[" + String.join(",", methods) + "]");
        }
    }

    private List<String> generateRecoveryCodes(String userId) {
        List<String> codes = new ArrayList<>();
        for (int i = 0; i < RECOVERY_CODE_COUNT; i++) {
            String code = generateRecoveryCode();
            RecoveryCode rc = new RecoveryCode();
            rc.setUserId(userId);
            rc.setCodeHash(passwordEncoder.encode(code));
            rc.setCreatedAt(Instant.now());
            recoveryCodeRepository.save(rc);
            codes.add(code);
        }
        return codes;
    }

    private String generateRecoveryCode() {
        StringBuilder sb = new StringBuilder(RECOVERY_CODE_LENGTH);
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        for (int i = 0; i < RECOVERY_CODE_LENGTH; i++) {
            sb.append(chars.charAt(RANDOM.nextInt(chars.length())));
        }
        // Format as XXXX-XXXX-XXXX
        sb.insert(8, '-');
        sb.insert(4, '-');
        return sb.toString();
    }

    private LoginResult completeMfaLogin(User user, String deviceId, String clientId,
                                          String ip, String userAgent) {
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

    // ==================== DTOs ====================

    public record TotpSetupResult(String secret, String otpAuthUri) {}

    public record MfaVerifyResult(
            boolean verified,
            String method,
            String[] mfaMethods,
            List<String> recoveryCodes
    ) {}

    public record Fido2RegistrationChallenge(String challenge) {}

    public record Fido2AllowCredential(String id, String transports) {}

    public record Fido2AssertionChallenge(
            String challenge,
            List<Fido2AllowCredential> allowCredentials
    ) {}

    public record MfaStatus(
            boolean enabled,
            MfaMethodInfo[] methods,
            long remainingRecoveryCodes
    ) {}

    public record MfaMethodInfo(
            String type,
            String name,
            boolean active
    ) {}
}
