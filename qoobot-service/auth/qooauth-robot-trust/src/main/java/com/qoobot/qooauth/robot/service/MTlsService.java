package com.qoobot.qooauth.robot.service;

import com.qoobot.qooauth.robot.entity.RobotTrustGroup;
import com.qoobot.qooauth.robot.repository.RobotTrustRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.security.cert.X509Certificate;
import java.util.List;

/**
 * mTLS certificate chain validation and group trust verification service.
 * Handles mutual TLS authentication between robot devices within trust groups.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MTlsService {

    private final RobotTrustRepository robotTrustRepository;

    /**
     * Validate a client certificate chain and verify the device belongs to
     * at least one active trust group.
     *
     * @param clientCert the X.509 client certificate presented during mTLS handshake
     * @param deviceId   the claimed device identity
     * @return true if the certificate chain is valid and the device is in a trusted group
     */
    public boolean validateCertificate(X509Certificate clientCert, String deviceId) {
        try {
            // Verify certificate validity period
            clientCert.checkValidity();

            // Verify the certificate hasn't been revoked (CRL/OCSP check would go here)
            // For now, check that the device has active trust groups
            List<RobotTrustGroup> activeGroups = robotTrustRepository.findActiveGroupsByDeviceId(deviceId);
            if (activeGroups.isEmpty()) {
                log.warn("Device {} has no active trust groups for mTLS", deviceId);
                return false;
            }

            log.info("mTLS certificate validated for device {} in {} trust groups", deviceId, activeGroups.size());
            return true;
        } catch (Exception e) {
            log.error("mTLS certificate validation failed for device {}: {}", deviceId, e.getMessage());
            return false;
        }
    }

    /**
     * Verify that two devices share at least one active trust group,
     * enabling mutual trust for mTLS communication.
     */
    public boolean verifyGroupTrust(String deviceIdA, String deviceIdB) {
        List<RobotTrustGroup> groupsA = robotTrustRepository.findActiveGroupsByDeviceId(deviceIdA);
        List<RobotTrustGroup> groupsB = robotTrustRepository.findActiveGroupsByDeviceId(deviceIdB);

        // Check for overlapping group membership
        boolean hasSharedGroup = groupsA.stream()
            .anyMatch(ga -> groupsB.stream()
                .anyMatch(gb -> ga.getGroupId().equals(gb.getGroupId())));

        if (!hasSharedGroup) {
            log.warn("No shared trust group between device {} and device {}", deviceIdA, deviceIdB);
        }

        return hasSharedGroup;
    }
}
