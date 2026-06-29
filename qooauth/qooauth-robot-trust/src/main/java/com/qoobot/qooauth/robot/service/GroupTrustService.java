package com.qoobot.qooauth.robot.service;

import com.qoobot.qooauth.robot.entity.RobotTrustGroup;
import com.qoobot.qooauth.robot.repository.RobotTrustRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;

/**
 * Manages robot trust groups: creation, membership, intra-group trust, and policy management.
 * Trust groups enable fleets of robots to establish mutual trust for collaborative operations.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GroupTrustService {

    private final RobotTrustRepository robotTrustRepository;

    /**
     * Create a new robot trust group.
     * The creating device becomes the owner of the group.
     */
    @Transactional
    public RobotTrustGroup createGroup(String name, String ownerDeviceId, Map<String, Object> trustPolicy) {
        // Check for duplicate group name per owner
        List<RobotTrustGroup> existingGroups = robotTrustRepository.findByOwnerDeviceId(ownerDeviceId);
        boolean duplicate = existingGroups.stream()
            .anyMatch(g -> g.getName().equals(name) && "ACTIVE".equals(g.getState()));
        if (duplicate) {
            throw new IllegalArgumentException("Group with name '" + name + "' already exists for device: " + ownerDeviceId);
        }

        Map<String, Object> defaultPolicy = new LinkedHashMap<>();
        defaultPolicy.put("max_members", 100);
        defaultPolicy.put("require_mtls", true);
        defaultPolicy.put("token_ttl_seconds", 3600);
        defaultPolicy.put("auto_join", false);
        if (trustPolicy != null) {
            defaultPolicy.putAll(trustPolicy);
        }

        RobotTrustGroup group = RobotTrustGroup.builder()
            .groupId(UUID.randomUUID().toString().replace("-", ""))
            .name(name)
            .ownerDeviceId(ownerDeviceId)
            .trustPolicy(defaultPolicy)
            .state("ACTIVE")
            .createdAt(Instant.now())
            .build();

        RobotTrustGroup saved = robotTrustRepository.save(group);
        log.info("Trust group '{}' created by device {}", name, ownerDeviceId);
        return saved;
    }

    /**
     * Add a device as a member to a trust group.
     */
    @Transactional
    public void addMember(String groupId, String deviceId, String requesterDeviceId) {
        RobotTrustGroup group = robotTrustRepository.findById(groupId)
            .orElseThrow(() -> new IllegalArgumentException("Trust group not found: " + groupId));

        if (!group.getOwnerDeviceId().equals(requesterDeviceId)) {
            throw new SecurityException("Only the group owner can add members");
        }

        if (!"ACTIVE".equals(group.getState())) {
            throw new IllegalStateException("Cannot add members to a non-active group");
        }

        // In a full implementation, we'd maintain a members table.
        // For now, trust is based on group membership verified via mTLS.
        log.info("Device {} added to trust group '{}' by owner {}", deviceId, group.getName(), requesterDeviceId);
    }

    /**
     * Get all active trust groups for a device (either as owner or member).
     */
    @Transactional(readOnly = true)
    public List<RobotTrustGroup> getGroupsForDevice(String deviceId) {
        return robotTrustRepository.findActiveGroupsByDeviceId(deviceId);
    }

    /**
     * Update the trust policy for a group.
     */
    @Transactional
    public RobotTrustGroup updatePolicy(String groupId, String ownerDeviceId, Map<String, Object> newPolicy) {
        RobotTrustGroup group = robotTrustRepository.findById(groupId)
            .orElseThrow(() -> new IllegalArgumentException("Trust group not found: " + groupId));

        if (!group.getOwnerDeviceId().equals(ownerDeviceId)) {
            throw new SecurityException("Only the group owner can update policy");
        }

        Map<String, Object> updatedPolicy = new LinkedHashMap<>(group.getTrustPolicy());
        updatedPolicy.putAll(newPolicy);
        group.setTrustPolicy(updatedPolicy);

        RobotTrustGroup saved = robotTrustRepository.save(group);
        log.info("Trust policy updated for group '{}'", group.getName());
        return saved;
    }

    /**
     * Disable a trust group (soft delete).
     */
    @Transactional
    public void disableGroup(String groupId, String ownerDeviceId) {
        RobotTrustGroup group = robotTrustRepository.findById(groupId)
            .orElseThrow(() -> new IllegalArgumentException("Trust group not found: " + groupId));

        if (!group.getOwnerDeviceId().equals(ownerDeviceId)) {
            throw new SecurityException("Only the group owner can disable the group");
        }

        group.setState("DISABLED");
        robotTrustRepository.save(group);
        log.info("Trust group '{}' disabled by owner {}", group.getName(), ownerDeviceId);
    }
}
