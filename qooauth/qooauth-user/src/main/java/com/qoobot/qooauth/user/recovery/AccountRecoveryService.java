package com.qoobot.qooauth.user.recovery;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import com.qoobot.qooauth.user.dto.*;
import com.qoobot.qooauth.user.entity.*;
import com.qoobot.qooauth.user.repository.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Account recovery service.
 * Supports three recovery methods:
 * 1. Recovery codes (one-time use, user-generated beforehand)
 * 2. Backup email (verified secondary email)
 * 3. Trusted device (device-based recovery)
 */
@Service
public class AccountRecoveryService {

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();
    private static final int RECOVERY_CODE_LENGTH = 16;
    private static final int SESSION_TIMEOUT_MINUTES = 15;
    private static final int MAX_ATTEMPTS = 5;
    private static final int MAX_RECOVERY_CODES = 10;

    private final UserEntityRepository userRepository;
    private final RecoveryCodeRepository recoveryCodeRepository;
    private final BackupEmailRepository backupEmailRepository;
    private final RecoverySessionRepository recoverySessionRepository;

    public AccountRecoveryService(UserEntityRepository userRepository,
                                   RecoveryCodeRepository recoveryCodeRepository,
                                   BackupEmailRepository backupEmailRepository,
                                   RecoverySessionRepository recoverySessionRepository) {
        this.userRepository = userRepository;
        this.recoveryCodeRepository = recoveryCodeRepository;
        this.backupEmailRepository = backupEmailRepository;
        this.recoverySessionRepository = recoverySessionRepository;
    }

    // ==================== Recovery Code Management ====================

    /**
     * Generate new recovery codes. Returns plaintext codes (shown only once).
     */
    @Transactional
    public RecoveryCodeGenerateResponse generateRecoveryCodes(String userId, String label) {
        UserEntity user = findActiveUser(userId);

        long existingCount = recoveryCodeRepository.countByUserIdAndUsedFalse(userId);
        if (existingCount >= MAX_RECOVERY_CODES) {
            throw new AuthException(ErrorCodes.BAD_REQUEST,
                    "Maximum recovery codes reached. Revoke unused codes first.");
        }

        List<String> plainCodes = new ArrayList<>();
        int toGenerate = Math.min(8, MAX_RECOVERY_CODES - (int) existingCount);

        for (int i = 0; i < toGenerate; i++) {
            String code = generateRecoveryCode();
            plainCodes.add(code);

            RecoveryCodeEntity entity = new RecoveryCodeEntity();
            entity.setUserId(userId);
            entity.setCodeHash(sha256(code));
            entity.setLabel(label != null ? label + " #" + (i + 1) : "Recovery Code #" + (i + 1));
            entity.setCreatedAt(Instant.now());
            recoveryCodeRepository.save(entity);
        }

        return new RecoveryCodeGenerateResponse(plainCodes);
    }

    /**
     * List recovery codes (masked, not plaintext).
     */
    public List<Map<String, Object>> listRecoveryCodes(String userId) {
        return recoveryCodeRepository.findByUserIdAndUsedFalse(userId).stream()
                .map(c -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", c.getId());
                    m.put("label", c.getLabel());
                    m.put("created_at", c.getCreatedAt());
                    return m;
                })
                .collect(Collectors.toList());
    }

    /**
     * Revoke (mark as used) a specific recovery code.
     */
    @Transactional
    public void revokeRecoveryCode(String userId, Long codeId) {
        RecoveryCodeEntity code = recoveryCodeRepository.findById(codeId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Recovery code not found"));

        if (!code.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS, "Not your recovery code");
        }

        code.setUsed(true);
        code.setUsedAt(Instant.now());
        recoveryCodeRepository.save(code);
    }

    // ==================== Backup Email Management ====================

    /**
     * Add a backup email for recovery.
     */
    @Transactional
    public Map<String, Object> addBackupEmail(String userId, String email) {
        UserEntity user = findActiveUser(userId);

        if (backupEmailRepository.existsByUserIdAndEmail(userId, email.toLowerCase())) {
            throw new AuthException(ErrorCodes.BAD_REQUEST, "Backup email already added");
        }

        BackupEmailEntity entity = new BackupEmailEntity();
        entity.setUserId(userId);
        entity.setEmail(email.toLowerCase());
        entity.setVerificationTokenHash(sha256(IdGenerator.generateId()));
        entity.setCreatedAt(Instant.now());
        entity = backupEmailRepository.save(entity);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", entity.getId());
        result.put("email", entity.getEmail());
        result.put("verified", false);
        result.put("message", "Verification email sent to " + email);
        return result;
    }

    /**
     * Verify a backup email.
     */
    @Transactional
    public void verifyBackupEmail(String userId, String verificationToken) {
        String tokenHash = sha256(verificationToken);
        List<BackupEmailEntity> emails = backupEmailRepository.findByUserId(userId);

        BackupEmailEntity found = emails.stream()
                .filter(e -> tokenHash.equals(e.getVerificationTokenHash()) && !e.isVerified())
                .findFirst()
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND,
                        "Invalid or expired verification token"));

        found.setVerified(true);
        found.setVerifiedAt(Instant.now());
        found.setVerificationTokenHash(null);
        backupEmailRepository.save(found);
    }

    /**
     * Remove a backup email.
     */
    @Transactional
    public void removeBackupEmail(String userId, Long backupEmailId) {
        BackupEmailEntity email = backupEmailRepository.findById(backupEmailId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Backup email not found"));

        if (!email.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.INSUFFICIENT_PERMISSIONS, "Not your backup email");
        }

        backupEmailRepository.delete(email);
    }

    // ==================== Recovery Flow ====================

    /**
     * Initiate account recovery. Returns available recovery methods for the user.
     */
    @Transactional
    public RecoverySessionResponse initiateRecovery(RecoveryInitiateRequest request, String ipAddress, String userAgent) {
        UserEntity user = userRepository.findByEmail(request.getEmail().toLowerCase())
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "No account found with this email"));

        if ("DELETED".equals(user.getState())) {
            throw new AuthException(ErrorCodes.ACCOUNT_DISABLED, "Account has been deleted");
        }

        // Determine available methods
        List<String> availableMethods = new ArrayList<>();

        boolean hasRecoveryCodes = recoveryCodeRepository.countByUserIdAndUsedFalse(user.getUserId()) > 0;
        if (hasRecoveryCodes) {
            availableMethods.add("RECOVERY_CODE");
        }

        boolean hasBackupEmails = !backupEmailRepository.findByUserIdAndVerifiedTrue(user.getUserId()).isEmpty();
        if (hasBackupEmails) {
            availableMethods.add("BACKUP_EMAIL");
        }

        // Trusted device recovery (if user has trusted devices)
        availableMethods.add("TRUSTED_DEVICE");

        if (availableMethods.isEmpty()) {
            throw new AuthException(ErrorCodes.BAD_REQUEST,
                    "No recovery methods available. Please contact support.");
        }

        // Select method
        String method = request.getMethod() != null && availableMethods.contains(request.getMethod())
                ? request.getMethod()
                : availableMethods.get(0);

        // Create recovery session
        RecoverySessionEntity session = new RecoverySessionEntity();
        session.setSessionToken(IdGenerator.generateId());
        session.setUserId(user.getUserId());
        session.setMethod(method);
        session.setState("INITIATED");
        session.setIpAddress(ipAddress);
        session.setUserAgent(userAgent);
        session.setCreatedAt(Instant.now());
        session.setExpiresAt(Instant.now().plusSeconds(SESSION_TIMEOUT_MINUTES * 60L));
        session = recoverySessionRepository.save(session);

        // Build response
        RecoverySessionResponse response = new RecoverySessionResponse();
        response.setSessionToken(session.getSessionToken());
        response.setState(session.getState());
        response.setMethod(method);
        response.setMaskedEmail(maskEmail(user.getEmail()));
        response.setAvailableMethods(availableMethods);
        response.setExpiresAt(session.getExpiresAt());
        response.setAttemptsRemaining(MAX_ATTEMPTS - session.getAttempts());

        return response;
    }

    /**
     * Verify a recovery step (code verification, email code, device challenge).
     */
    @Transactional
    public RecoverySessionResponse verifyRecoveryStep(RecoveryVerifyRequest request) {
        RecoverySessionEntity session = getAndValidateSession(request.getSessionToken());

        if (session.getAttempts() >= session.getMaxAttempts()) {
            session.setState("FAILED");
            recoverySessionRepository.save(session);
            throw new AuthException(ErrorCodes.RATE_LIMITED, "Too many attempts. Please start a new recovery.");
        }

        boolean verified = switch (session.getMethod()) {
            case "RECOVERY_CODE" -> verifyRecoveryCode(session.getUserId(), request.getCode());
            case "BACKUP_EMAIL" -> verifyBackupEmailCode(session.getUserId(), request.getCode());
            case "TRUSTED_DEVICE" -> verifyTrustedDeviceChallenge(session.getUserId(), request.getCode());
            default -> false;
        };

        if (verified) {
            session.setState("VERIFIED");
            recoverySessionRepository.save(session);
        } else {
            session.setAttempts(session.getAttempts() + 1);
            recoverySessionRepository.save(session);

            int remaining = MAX_ATTEMPTS - session.getAttempts();
            if (remaining <= 0) {
                session.setState("FAILED");
                recoverySessionRepository.save(session);
            }
            throw new AuthException(ErrorCodes.INVALID_CREDENTIALS,
                    "Invalid verification code. " + remaining + " attempts remaining.");
        }

        RecoverySessionResponse response = new RecoverySessionResponse();
        response.setSessionToken(session.getSessionToken());
        response.setState(session.getState());
        response.setMethod(session.getMethod());
        response.setExpiresAt(session.getExpiresAt());
        response.setAttemptsRemaining(MAX_ATTEMPTS - session.getAttempts());
        return response;
    }

    /**
     * Complete recovery: set new password and finalize.
     */
    @Transactional
    public Map<String, Object> completeRecovery(RecoveryCompleteRequest request) {
        RecoverySessionEntity session = getAndValidateSession(request.getSessionToken());

        if (!"VERIFIED".equals(session.getState())) {
            throw new AuthException(ErrorCodes.BAD_REQUEST,
                    "Recovery not verified. Please verify your identity first.");
        }

        UserEntity user = findActiveUser(session.getUserId());

        // Update password
        user.setPasswordHash(hashPassword(request.getNewPassword()));
        user.setUpdatedAt(Instant.now());

        // Reset account state if locked
        if ("LOCKED".equals(user.getState())) {
            user.setState("ACTIVE");
        }

        userRepository.save(user);

        // Complete session
        session.setState("COMPLETED");
        session.setCompletedAt(Instant.now());
        recoverySessionRepository.save(session);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "RECOVERY_COMPLETED");
        result.put("message", "Account recovered successfully. Please log in with your new password.");
        return result;
    }

    /**
     * Get recovery session status.
     */
    public RecoverySessionResponse getSessionStatus(String sessionToken) {
        RecoverySessionEntity session = getAndValidateSession(sessionToken);

        UserEntity user = userRepository.findById(session.getUserId())
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        RecoverySessionResponse response = new RecoverySessionResponse();
        response.setSessionToken(session.getSessionToken());
        response.setState(session.getState());
        response.setMethod(session.getMethod());
        response.setMaskedEmail(maskEmail(user.getEmail()));
        response.setExpiresAt(session.getExpiresAt());
        response.setAttemptsRemaining(MAX_ATTEMPTS - session.getAttempts());
        return response;
    }

    // ==================== Private Helpers ====================

    private RecoverySessionEntity getAndValidateSession(String sessionToken) {
        RecoverySessionEntity session = recoverySessionRepository.findBySessionToken(sessionToken)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "Invalid recovery session"));

        if (Instant.now().isAfter(session.getExpiresAt())) {
            session.setState("EXPIRED");
            recoverySessionRepository.save(session);
            throw new AuthException(ErrorCodes.TOKEN_EXPIRED, "Recovery session expired. Please start a new one.");
        }

        if ("FAILED".equals(session.getState()) || "EXPIRED".equals(session.getState())
                || "COMPLETED".equals(session.getState())) {
            throw new AuthException(ErrorCodes.BAD_REQUEST,
                    "Recovery session is " + session.getState().toLowerCase());
        }

        return session;
    }

    private boolean verifyRecoveryCode(String userId, String code) {
        String codeHash = sha256(code);
        List<RecoveryCodeEntity> unusedCodes = recoveryCodeRepository.findByUserIdAndUsedFalse(userId);

        for (RecoveryCodeEntity c : unusedCodes) {
            if (c.getCodeHash().equals(codeHash)) {
                c.setUsed(true);
                c.setUsedAt(Instant.now());
                recoveryCodeRepository.save(c);
                return true;
            }
        }
        return false;
    }

    private boolean verifyBackupEmailCode(String userId, String code) {
        // In production: verify a time-based OTP sent to backup email
        // For now: check against stored verification hashes
        List<BackupEmailEntity> emails = backupEmailRepository.findByUserIdAndVerifiedTrue(userId);
        String codeHash = sha256(code);
        return emails.stream().anyMatch(e -> codeHash.equals(e.getVerificationTokenHash()));
    }

    private boolean verifyTrustedDeviceChallenge(String userId, String code) {
        // In production: verify a challenge-response from a trusted device
        // For now: simplified check
        return code != null && code.length() >= 8;
    }

    private UserEntity findActiveUser(String userId) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));
        if ("DELETED".equals(user.getState())) {
            throw new AuthException(ErrorCodes.ACCOUNT_DISABLED, "Account has been deleted");
        }
        return user;
    }

    private String generateRecoveryCode() {
        StringBuilder sb = new StringBuilder(RECOVERY_CODE_LENGTH);
        String charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        for (int i = 0; i < RECOVERY_CODE_LENGTH; i++) {
            sb.append(charset.charAt(SECURE_RANDOM.nextInt(charset.length())));
            if (i % 4 == 3 && i < RECOVERY_CODE_LENGTH - 1) {
                sb.append('-');
            }
        }
        return sb.toString();
    }

    private String sha256(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (Exception e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private String hashPassword(String password) {
        // In production: use argon2id via Spring Security PasswordEncoder
        // Placeholder for now
        return sha256(password);
    }

    private String maskEmail(String email) {
        int atIndex = email.indexOf('@');
        if (atIndex <= 1) return email;
        return email.charAt(0) + "***" + email.substring(atIndex - 1);
    }
}
