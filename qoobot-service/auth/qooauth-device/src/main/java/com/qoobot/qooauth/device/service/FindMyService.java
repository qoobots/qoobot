package com.qoobot.qooauth.device.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.device.entity.Device;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Device location tracking and Find My functionality.
 * <p>
 * Provides stubs for:
 * <ul>
 *   <li>Location reporting and retrieval</li>
 *   <li>Remote ring / sound alert</li>
 *   <li>Lost mode activation</li>
 *   <li>Remote wipe trigger</li>
 * </ul>
 * <p>
 * In production, these would integrate with a push-notification service
 * (e.g. FCM/APNs via gRPC to qoobody) and a location data store (e.g.
 * PostGIS or Redis geo-index).
 */
@Service
public class FindMyService {

    private static final Logger log = LoggerFactory.getLogger(FindMyService.class);

    private final DeviceService deviceService;

    /** In-memory store for pending commands (production: use Redis pub/sub). */
    private final ConcurrentHashMap<String, PendingCommand> pendingCommands = new ConcurrentHashMap<>();

    public FindMyService(DeviceService deviceService) {
        this.deviceService = deviceService;
    }

    // ========================================================================
    //  Location
    // ========================================================================

    /**
     * Report the device's current location.
     *
     * @param deviceId  the device ID
     * @param latitude  decimal latitude
     * @param longitude decimal longitude
     * @param accuracy  accuracy in meters (optional)
     */
    public void reportLocation(String deviceId, double latitude, double longitude, Double accuracy) {
        Device device = deviceService.findByDeviceId(deviceId);

        String locationJson = String.format(
                "{\"lat\":%.7f,\"lng\":%.7f,\"accuracy\":%s,\"timestamp\":\"%s\"}",
                latitude, longitude,
                accuracy != null ? String.format("%.1f", accuracy) : "null",
                java.time.Instant.now().toString());

        deviceService.updateLocation(deviceId, locationJson);
        log.debug("Location updated for device {}: ({}, {})", deviceId, latitude, longitude);
    }

    /**
     * Get the last known location of a device.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user (must own the device)
     * @return last known location as a JSON object string, or null
     */
    public String getLastLocation(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can view location");
        }

        return device.getLastLocation();
    }

    // ========================================================================
    //  Remote ring
    // ========================================================================

    /**
     * Send a remote ring command to the device.
     * <p>
     * The device will play an audible alert to help the user locate it.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     * @return command ID for tracking
     */
    public String remoteRing(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can trigger remote ring");
        }

        String commandId = "ring_" + java.util.UUID.randomUUID().toString().substring(0, 8);
        pendingCommands.put(deviceId, new PendingCommand(commandId, "RING",
                Map.of("duration_seconds", "30")));

        log.info("Remote ring command {} sent to device {}", commandId, deviceId);
        return commandId;
    }

    // ========================================================================
    //  Lost mode
    // ========================================================================

    /**
     * Enable Lost Mode on a device.
     * <p>
     * In lost mode, the device locks itself and displays a contact message.
     *
     * @param deviceId       the device ID
     * @param userId         the requesting user
     * @param contactMessage message to display on the lost device
     * @param contactPhone   optional contact phone number
     */
    public void enableLostMode(String deviceId, String userId, String contactMessage, String contactPhone) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can enable lost mode");
        }

        deviceService.markLost(deviceId, userId);

        String commandId = "lost_" + java.util.UUID.randomUUID().toString().substring(0, 8);
        pendingCommands.put(deviceId, new PendingCommand(commandId, "LOST_MODE",
                Map.of("contact_message", contactMessage != null ? contactMessage : "",
                        "contact_phone", contactPhone != null ? contactPhone : "")));

        log.info("Lost mode enabled for device {} with command {}", deviceId, commandId);
    }

    /**
     * Disable Lost Mode on a device.
     */
    public void disableLostMode(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can disable lost mode");
        }

        // Transition back to BOUND if currently LOST
        if (device.getState() == com.qoobot.qooauth.common.enums.DeviceState.LOST) {
            // State transition handled by DeviceService
        }

        log.info("Lost mode disabled for device {}", deviceId);
    }

    // ========================================================================
    //  Remote wipe
    // ========================================================================

    /**
     * Trigger a remote wipe command.
     * <p>
     * The device will factory-reset itself and erase all local data.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     * @return command ID for tracking
     */
    public String remoteWipe(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can trigger remote wipe");
        }

        deviceService.wipe(deviceId, userId);

        String commandId = "wipe_" + java.util.UUID.randomUUID().toString().substring(0, 8);
        pendingCommands.put(deviceId, new PendingCommand(commandId, "WIPE",
                Map.of("preserve_esim", "false")));

        log.info("Remote wipe command {} sent to device {}", commandId, deviceId);
        return commandId;
    }

    // ========================================================================
    //  Guest mode (stub)
    // ========================================================================

    /**
     * Enable guest mode — allows temporary limited access without binding.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     * @return guest access token
     */
    public String enableGuestMode(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can manage guest mode");
        }

        String guestToken = "guest_" + java.util.UUID.randomUUID().toString();
        log.info("Guest mode enabled for device {}: token={}...", deviceId, guestToken.substring(0, 16));
        return guestToken;
    }

    /**
     * Disable guest mode.
     */
    public void disableGuestMode(String deviceId, String userId) {
        Device device = deviceService.findByDeviceId(deviceId);

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can manage guest mode");
        }

        log.info("Guest mode disabled for device {}", deviceId);
    }

    // ========================================================================
    //  Pending command model
    // ========================================================================

    private record PendingCommand(String commandId, String type, Map<String, String> params) {}
}
