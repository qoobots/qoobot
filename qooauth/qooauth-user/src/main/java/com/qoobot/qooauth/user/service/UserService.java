package com.qoobot.qooauth.user.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.user.entity.UserEntity;
import com.qoobot.qooauth.user.repository.UserEntityRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Optional;

/**
 * User profile management service.
 * Handles profile updates, account recovery, and account deletion.
 */
@Service
public class UserService {

    private final UserEntityRepository userRepository;

    public UserService(UserEntityRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Get user profile by ID.
     */
    public Optional<UserProfile> getUserProfile(String userId) {
        return userRepository.findById(userId)
                .filter(u -> !"DELETED".equals(u.getState()))
                .map(this::toProfile);
    }

    /**
     * Get user by email.
     */
    public Optional<UserProfile> getUserByEmail(String email) {
        return userRepository.findByEmail(email.toLowerCase())
                .filter(u -> !"DELETED".equals(u.getState()))
                .map(this::toProfile);
    }

    /**
     * Update user profile.
     */
    @Transactional
    public UserProfile updateProfile(String userId, String nickname, String language,
                                      String timezone, String avatarHash) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        if (nickname != null && !nickname.isEmpty()) {
            if (nickname.length() > 64) {
                throw new AuthException(ErrorCodes.NICKNAME_TOO_LONG,
                        "Nickname must be 64 characters or fewer");
            }
            user.setNickname(nickname);
        }
        if (language != null) {
            user.setLanguage(language);
        }
        if (timezone != null) {
            user.setTimezone(timezone);
        }
        if (avatarHash != null) {
            user.setAvatarHash(avatarHash);
        }

        user.setUpdatedAt(Instant.now());
        user = userRepository.save(user);

        return toProfile(user);
    }

    /**
     * Initiate account deletion (30-day grace period).
     */
    @Transactional
    public void requestAccountDeletion(String userId) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        // Mark for deletion with grace period
        user.setState("DELETED");
        user.setDeletedAt(Instant.now().plusSeconds(30 * 86400)); // 30 days
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);
    }

    /**
     * Verify email address.
     */
    @Transactional
    public void verifyEmail(String userId) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new AuthException(ErrorCodes.NOT_FOUND, "User not found"));

        user.setEmailVerified(true);
        if ("EMAIL_VERIFICATION_PENDING".equals(user.getState())) {
            user.setState("ACTIVE");
        }
        user.setUpdatedAt(Instant.now());
        userRepository.save(user);
    }

    private UserProfile toProfile(UserEntity user) {
        return new UserProfile(
                user.getUserId(),
                user.getEmail(),
                user.getNickname(),
                user.getAvatarHash() != null
                        ? "https://cdn.qoobot.com/avatars/" + user.getAvatarHash()
                        : null,
                user.getLanguage(),
                user.getTimezone(),
                user.isEmailVerified(),
                user.isPhoneVerified(),
                user.isMfaEnabled(),
                user.getState(),
                user.getCreatedAt(),
                user.getLastLoginAt()
        );
    }

    public record UserProfile(
            String sub,
            String email,
            String nickname,
            String avatarUrl,
            String language,
            String timezone,
            boolean emailVerified,
            boolean phoneVerified,
            boolean mfaEnabled,
            String state,
            Instant createdAt,
            Instant lastLoginAt
    ) {}
}
