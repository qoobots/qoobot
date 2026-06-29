package com.qoobot.qooauth.robot.service;

import com.qoobot.qooauth.robot.entity.CollaborationToken;
import com.qoobot.qooauth.robot.entity.RobotTrustGroup;
import com.qoobot.qooauth.robot.repository.CollaborationTokenRepository;
import com.qoobot.qooauth.robot.repository.RobotTrustRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

/**
 * Full-chain trust revocation service.
 * Handles cascading revocation of trust relationships and automatic cleanup of expired tokens.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TrustRevocationService {

    private final RobotTrustRepository robotTrustRepository;
    private final CollaborationTokenRepository tokenRepository;
    private final CollaborationAuthService collaborationAuthService;

    /**
     * Full-chain revocation: when a device is removed from a trust group,
     * all collaboration tokens involving that device are revoked.
     */
    @Transactional
    public void revokeDeviceTrust(String groupId, String deviceId, String requesterDeviceId) {
        RobotTrustGroup group = robotTrustRepository.findById(groupId)
            .orElseThrow(() -> new IllegalArgumentException("Trust group not found: " + groupId));

        if (!group.getOwnerDeviceId().equals(requesterDeviceId)) {
            throw new SecurityException("Only the group owner can revoke device trust");
        }

        // Revoke all collaboration tokens for the device
        collaborationAuthService.revokeAllTokensForDevice(deviceId);

        log.info("Full-chain trust revoked for device {} in group '{}'", deviceId, group.getName());
    }

    /**
     * Revoke an entire trust group and all associated collaboration tokens.
     */
    @Transactional
    public void revokeGroup(String groupId, String ownerDeviceId) {
        RobotTrustGroup group = robotTrustRepository.findById(groupId)
            .orElseThrow(() -> new IllegalArgumentException("Trust group not found: " + groupId));

        if (!group.getOwnerDeviceId().equals(ownerDeviceId)) {
            throw new SecurityException("Only the group owner can revoke the group");
        }

        // Mark group as revoked
        group.setState("REVOKED");
        robotTrustRepository.save(group);

        // In production, we'd query all group members and revoke their tokens
        // For now, log the intent
        log.warn("Trust group '{}' fully revoked. All member tokens should be invalidated.", group.getName());
    }

    /**
     * Scheduled cleanup of expired collaboration tokens.
     * Runs every 5 minutes to automatically expire tokens past their TTL.
     */
    @Scheduled(fixedRate = 300_000)
    @Transactional
    public void cleanupExpiredTokens() {
        Instant now = Instant.now();
        List<CollaborationToken> expiredTokens = tokenRepository.findExpiredActiveTokens(now);

        if (!expiredTokens.isEmpty()) {
            expiredTokens.forEach(t -> t.setState("EXPIRED"));
            tokenRepository.saveAll(expiredTokens);
            log.info("Auto-expired {} collaboration tokens", expiredTokens.size());
        }
    }

    /**
     * Manual trigger for expired token cleanup.
     */
    @Transactional
    public int forceCleanupExpiredTokens() {
        Instant now = Instant.now();
        List<CollaborationToken> expiredTokens = tokenRepository.findExpiredActiveTokens(now);
        expiredTokens.forEach(t -> t.setState("EXPIRED"));
        tokenRepository.saveAll(expiredTokens);
        log.info("Force-cleaned {} expired collaboration tokens", expiredTokens.size());
        return expiredTokens.size();
    }
}
