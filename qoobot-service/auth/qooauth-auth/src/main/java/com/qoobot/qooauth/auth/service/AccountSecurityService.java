package com.qoobot.qooauth.auth.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qooauth.auth.entity.LoginHistory;
import com.qoobot.qooauth.auth.entity.TrustedDevice;
import com.qoobot.qooauth.auth.entity.User;
import com.qoobot.qooauth.auth.repository.LoginHistoryRepository;
import com.qoobot.qooauth.auth.repository.TrustedDeviceRepository;
import com.qoobot.qooauth.auth.repository.UserRepository;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Account security service.
 * Handles password changes, trusted device management, and login history.
 */
@Service
public class AccountSecurityService {

    private static final Logger log = LoggerFactory.getLogger(AccountSecurityService.class);
    private static final int PASSWORD_HISTORY_LIMIT = 5;
    private static final int MAX_TRUSTED_DEVICES = 20;

    private final UserRepository userRepository;
    private final TrustedDeviceRepository trustedDeviceRepository;
    private final LoginHistoryRepository loginHistoryRepository;
    private final PasswordService passwordService;
    private final ObjectMapper objectMapper;

    public AccountSecurityService(UserRepository userRepository,
                                  TrustedDeviceRepository trustedDeviceRepository,
                                  LoginHistoryRepository loginHistoryRepository,
                                  PasswordService passwordService,
                                  ObjectMapper objectMapper) {
        this.userRepository = userRepository;
        this.trustedDeviceRepository = trustedDeviceRepository;
        this.loginHistoryRepository = loginHistoryRepository;
        this.passwordService = passwordService;
        this.objectMapper = objectMapper;
    }

    // ========================================================================
    // Password Change
    // ========================================================================

    /**
     * Change password for an authenticated user.
     *
     * @param userId          the authenticated user's ID
     * @param currentPassword the current (old) password
     * @param newPassword     the desired new password
     * @param revokeSessions  if true, revoke all other sessions after change
     * @return timestamp of the change
     */
    @Transactional
    public Instant changePassword(String userId, String currentPassword,
                                   String newPassword, boolean revokeSessions) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.INVALID_CREDENTIALS, "User not found"));

        // 1. Verify current password
        if (!passwordService.verify(user.getPasswordHash(), currentPassword)) {
            throw new AuthException(ErrorCodes.INVALID_CREDENTIALS, "Current password is incorrect");
        }

        // 2. Validate new password strength
        if (!isStrongPassword(newPassword)) {
            throw new AuthException(ErrorCodes.WEAK_PASSWORD,
                    "New password must be at least 8 characters with upper, lower, digit, and special character");
        }

        // 3. Check new password is different from current
        if (passwordService.verify(user.getPasswordHash(), newPassword)) {
            throw new AuthException(ErrorCodes.PASSWORD_SAME_AS_CURRENT,
                    "New password must be different from current password");
        }

        // 4. Check password history (prevent reuse of last 5 passwords)
        List<String> history = parsePasswordHistory(user.getPasswordHistory());
        for (String oldHash : history) {
            if (passwordService.verify(oldHash, newPassword)) {
                throw new AuthException(ErrorCodes.PASSWORD_REUSED,
                        "Cannot reuse one of your last " + PASSWORD_HISTORY_LIMIT + " passwords");
            }
        }

        // 5. Add current hash to history, trim to limit
        history.add(0, user.getPasswordHash());
        if (history.size() > PASSWORD_HISTORY_LIMIT) {
            history = history.subList(0, PASSWORD_HISTORY_LIMIT);
        }

        // 6. Hash new password
        String newHash = passwordService.hash(newPassword);
        Instant now = Instant.now();

        // 7. Update user
        user.setPasswordHash(newHash);
        user.setPasswordChangedAt(now);
        user.setPasswordHistory(toJson(history));
        user.setUpdatedAt(now);
        userRepository.save(user);

        // 8. Optionally revoke other sessions (force re-login elsewhere)
        if (revokeSessions) {
            // session revocation is handled by caller via SessionService
        }

        log.info("Password changed for user {}", userId);
        return now;
    }

    // ========================================================================
    // Trusted Device Management
    // ========================================================================

    /**
     * Record or update a trusted device entry after successful login.
     */
    @Transactional
    public TrustedDevice recordTrustedDevice(String userId, String deviceId, String deviceName,
                                              String deviceType, String osName, String osVersion,
                                              String browserName, String browserVersion,
                                              String deviceModel, String fingerprint,
                                              String ipAddress, String userAgent) {
        // Hash the fingerprint for storage
        String fingerprintHash = hashFingerprint(fingerprint);

        // Check if this device already exists
        Optional<TrustedDevice> existing = trustedDeviceRepository
                .findByUserIdAndFingerprint(userId, fingerprintHash);

        if (existing.isPresent()) {
            TrustedDevice device = existing.get();
            device.setLastUsedAt(Instant.now());
            device.setIpAddress(ipAddress);
            device.setUserAgent(userAgent);
            if (deviceName != null) device.setDeviceName(deviceName);
            return trustedDeviceRepository.save(device);
        }

        // Enforce max trusted devices
        long count = trustedDeviceRepository.countByUserId(userId);
        if (count >= MAX_TRUSTED_DEVICES) {
            // Remove the least recently used device
            List<TrustedDevice> allDevices = trustedDeviceRepository
                    .findByUserIdOrderByLastUsedAtDesc(userId);
            if (!allDevices.isEmpty()) {
                TrustedDevice oldest = allDevices.get(allDevices.size() - 1);
                trustedDeviceRepository.delete(oldest);
            }
        }

        // Create new trusted device entry
        TrustedDevice device = new TrustedDevice();
        device.setDeviceId(deviceId != null ? deviceId : IdGenerator.generateDeviceId());
        device.setUserId(userId);
        device.setDeviceName(deviceName);
        device.setDeviceType(deviceType != null ? deviceType : "unknown");
        device.setOsName(osName);
        device.setOsVersion(osVersion);
        device.setBrowserName(browserName);
        device.setBrowserVersion(browserVersion);
        device.setDeviceModel(deviceModel);
        device.setFingerprint(fingerprintHash);
        device.setIpAddress(ipAddress);
        device.setUserAgent(userAgent);
        device.setTrusted(false); // Initially not trusted; user must explicitly trust
        device.setLastUsedAt(Instant.now());
        device.setCreatedAt(Instant.now());

        return trustedDeviceRepository.save(device);
    }

    /**
     * Get all devices for a user.
     */
    public List<TrustedDevice> getTrustedDevices(String userId) {
        return trustedDeviceRepository.findByUserIdOrderByLastUsedAtDesc(userId);
    }

    /**
     * Mark a specific device as trusted (for 2FA bypass).
     */
    @Transactional
    public void trustDevice(String userId, String deviceId) {
        TrustedDevice device = trustedDeviceRepository.findById(deviceId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Device not found"));

        if (!device.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Device not found");
        }

        device.setTrusted(true);
        trustedDeviceRepository.save(device);
    }

    /**
     * Remove a specific device.
     */
    @Transactional
    public void removeDevice(String userId, String deviceId) {
        TrustedDevice device = trustedDeviceRepository.findById(deviceId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Device not found"));

        if (!device.getUserId().equals(userId)) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND, "Device not found");
        }

        trustedDeviceRepository.delete(device);
    }

    /**
     * Remove all trusted devices for a user.
     */
    @Transactional
    public void removeAllDevices(String userId) {
        trustedDeviceRepository.deleteByUserId(userId);
    }

    /**
     * Check if a device fingerprint is trusted for 2FA bypass.
     */
    public boolean isDeviceTrusted(String userId, String fingerprint) {
        String fingerprintHash = hashFingerprint(fingerprint);
        return trustedDeviceRepository.findByUserIdAndFingerprint(userId, fingerprintHash)
                .map(TrustedDevice::isTrusted)
                .orElse(false);
    }

    // ========================================================================
    // Login History
    // ========================================================================

    /**
     * Record a successful login attempt.
     */
    @Transactional
    public LoginHistory recordLoginSuccess(String userId, String ipAddress, String userAgent,
                                            String deviceFingerprint, String deviceName,
                                            String clientId, boolean mfaUsed, String mfaMethod,
                                            String sessionId) {
        LoginHistory entry = new LoginHistory();
        entry.setLoginId(IdGenerator.generateLoginHistoryId());
        entry.setUserId(userId);
        entry.setSuccess(true);
        entry.setIpAddress(ipAddress);
        entry.setUserAgent(truncate(userAgent, 512));
        entry.setDeviceFingerprint(hashFingerprint(deviceFingerprint));
        entry.setDeviceName(deviceName);
        entry.setClientId(clientId);
        entry.setMfaUsed(mfaUsed);
        entry.setMfaMethod(mfaMethod);
        entry.setSessionId(sessionId);
        entry.setCreatedAt(Instant.now());

        return loginHistoryRepository.save(entry);
    }

    /**
     * Record a failed login attempt.
     */
    @Transactional
    public LoginHistory recordLoginFailure(String userId, String failureReason,
                                            String ipAddress, String userAgent,
                                            String deviceFingerprint, String deviceName,
                                            String clientId) {
        LoginHistory entry = new LoginHistory();
        entry.setLoginId(IdGenerator.generateLoginHistoryId());
        entry.setUserId(userId);
        entry.setSuccess(false);
        entry.setFailureReason(failureReason);
        entry.setIpAddress(ipAddress);
        entry.setUserAgent(truncate(userAgent, 512));
        entry.setDeviceFingerprint(hashFingerprint(deviceFingerprint));
        entry.setDeviceName(deviceName);
        entry.setClientId(clientId);
        entry.setCreatedAt(Instant.now());

        return loginHistoryRepository.save(entry);
    }

    /**
     * Get paginated login history for a user.
     */
    public Page<LoginHistory> getLoginHistory(String userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        return loginHistoryRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
    }

    /**
     * Get recent login failures from an IP (for brute-force detection).
     */
    public long getRecentFailuresFromIp(String ipAddress, int windowMinutes) {
        Instant since = Instant.now().minus(windowMinutes, ChronoUnit.MINUTES);
        return loginHistoryRepository
                .findByIpAddressAndSuccessFalseAndCreatedAtAfter(ipAddress, since)
                .size();
    }

    /**
     * Get login success count for a user.
     */
    public long getLoginSuccessCount(String userId) {
        return loginHistoryRepository.countByUserIdAndSuccess(userId, true);
    }

    // ========================================================================
    // Private Helpers
    // ========================================================================

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

    private List<String> parsePasswordHistory(String json) {
        if (json == null || json.isEmpty() || "[]".equals(json)) {
            return new ArrayList<>();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (JsonProcessingException e) {
            log.warn("Failed to parse password history, resetting", e);
            return new ArrayList<>();
        }
    }

    private String toJson(List<String> list) {
        try {
            return objectMapper.writeValueAsString(list);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize password history", e);
            return "[]";
        }
    }

    private String hashFingerprint(String fingerprint) {
        if (fingerprint == null || fingerprint.isEmpty()) return "";
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(fingerprint.getBytes(StandardCharsets.UTF_8));
            return bytesToHex(digest);
        } catch (NoSuchAlgorithmException e) {
            log.error("SHA-256 not available", e);
            return fingerprint;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private String truncate(String value, int maxLength) {
        if (value == null) return null;
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
