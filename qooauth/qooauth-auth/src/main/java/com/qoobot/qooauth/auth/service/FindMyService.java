package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Find My QooBot Service.
 *
 * Provides device location, remote ring, lost mode, and remote wipe.
 * Similar to Apple Find My network, but for QooBot robots and accessories.
 */
@Service
public class FindMyService {
    private static final Logger log = LoggerFactory.getLogger(FindMyService.class);

    /**
     * In-memory device location store. In production, use a geospatial database.
     */
    private final ConcurrentHashMap<String, DeviceLocation> locations = new ConcurrentHashMap<>();

    /**
     * Lost mode state per device.
     */
    private final ConcurrentHashMap<String, LostModeState> lostModes = new ConcurrentHashMap<>();

    /**
     * Remote wipe state per device.
     */
    private final ConcurrentHashMap<String, WipeState> wipeStates = new ConcurrentHashMap<>();

    // ============================================================
    //  Device Location
    // ============================================================

    /**
     * Update device location.
     */
    public DeviceLocation updateLocation(String deviceId, double latitude, double longitude,
                                          double altitude, double accuracy, String address) {
        DeviceLocation loc = new DeviceLocation();
        loc.deviceId = deviceId;
        loc.latitude = latitude;
        loc.longitude = longitude;
        loc.altitude = altitude;
        loc.accuracy = accuracy;
        loc.address = address;
        loc.updatedAt = Instant.now();

        locations.put(deviceId, loc);
        return loc;
    }

    /**
     * Get device's last known location.
     */
    public DeviceLocation getLocation(String deviceId) {
        return locations.get(deviceId);
    }

    /**
     * Get locations for all devices belonging to a user.
     */
    public List<DeviceLocation> getUserDeviceLocations(String userId, List<String> deviceIds) {
        List<DeviceLocation> result = new ArrayList<>();
        for (String deviceId : deviceIds) {
            DeviceLocation loc = locations.get(deviceId);
            if (loc != null) {
                result.add(loc);
            }
        }
        return result;
    }

    /**
     * Check if a device is nearby (within specified radius in meters).
     */
    public boolean isNearby(String deviceId, double latitude, double longitude, double radiusMeters) {
        DeviceLocation loc = locations.get(deviceId);
        if (loc == null) return false;

        double distance = haversineDistance(latitude, longitude, loc.latitude, loc.longitude);
        return distance <= radiusMeters;
    }

    // ============================================================
    //  Remote Ring
    // ============================================================

    /**
     * Trigger remote ring on a device.
     * The device should play a loud sound to help locate it.
     */
    public RingCommand triggerRing(String deviceId, int durationSeconds, int volume) {
        RingCommand cmd = new RingCommand();
        cmd.deviceId = deviceId;
        cmd.commandType = "RING";
        cmd.durationSeconds = Math.min(durationSeconds, 120); // Max 2 minutes
        cmd.volume = Math.min(volume, 100);
        cmd.issuedAt = Instant.now();
        cmd.commandId = UUID.randomUUID().toString();

        log.info("Remote ring triggered for device {}: {}s at volume {}%",
                deviceId, cmd.durationSeconds, cmd.volume);
        return cmd;
    }

    /**
     * Stop ringing.
     */
    public RingCommand stopRing(String deviceId) {
        RingCommand cmd = new RingCommand();
        cmd.deviceId = deviceId;
        cmd.commandType = "STOP_RING";
        cmd.durationSeconds = 0;
        cmd.volume = 0;
        cmd.issuedAt = Instant.now();
        cmd.commandId = UUID.randomUUID().toString();

        log.info("Remote ring stopped for device {}", deviceId);
        return cmd;
    }

    // ============================================================
    //  Lost Mode
    // ============================================================

    /**
     * Enable Lost Mode on a device.
     * The device will lock itself and display a message with contact info.
     */
    public LostModeState enableLostMode(String deviceId, String message,
                                          String contactPhone, String contactEmail) {
        LostModeState state = new LostModeState();
        state.deviceId = deviceId;
        state.enabled = true;
        state.message = message;
        state.contactPhone = contactPhone;
        state.contactEmail = contactEmail;
        state.enabledAt = Instant.now();
        state.lastLocationUpdate = Instant.now();

        lostModes.put(deviceId, state);

        // Also trigger remote ring briefly
        triggerRing(deviceId, 10, 80);

        log.warn("Lost Mode enabled for device {}: {}", deviceId, message);
        return state;
    }

    /**
     * Disable Lost Mode.
     */
    public LostModeState disableLostMode(String deviceId) {
        LostModeState state = lostModes.get(deviceId);
        if (state != null) {
            state.enabled = false;
            state.disabledAt = Instant.now();
            lostModes.put(deviceId, state);
        }

        log.info("Lost Mode disabled for device {}", deviceId);
        return state;
    }

    /**
     * Get Lost Mode status.
     */
    public LostModeState getLostModeStatus(String deviceId) {
        return lostModes.get(deviceId);
    }

    /**
     * Update location while in Lost Mode.
     */
    public void updateLostModeLocation(String deviceId, double latitude, double longitude) {
        LostModeState state = lostModes.get(deviceId);
        if (state != null && state.enabled) {
            state.lastLocation = new double[]{latitude, longitude};
            state.lastLocationUpdate = Instant.now();
            updateLocation(deviceId, latitude, longitude, 0, 0, null);
        }
    }

    // ============================================================
    //  Remote Wipe
    // ============================================================

    /**
     * Initiate remote wipe of a device.
     * This is a destructive operation — all data on the device will be erased.
     */
    public WipeState initiateWipe(String deviceId, String wipeCode) {
        // Verify wipe code (6-digit code sent to owner's trusted devices)
        if (wipeCode == null || wipeCode.length() != 6) {
            throw new IllegalArgumentException("Invalid wipe code");
        }

        WipeState state = new WipeState();
        state.deviceId = deviceId;
        state.state = "PENDING_CONFIRMATION";
        state.wipeCodeHash = hashWipeCode(wipeCode);
        state.initiatedAt = Instant.now();
        state.wipeCommandId = UUID.randomUUID().toString();

        wipeStates.put(deviceId, state);
        log.warn("Remote wipe initiated for device {}: pending confirmation", deviceId);
        return state;
    }

    /**
     * Confirm remote wipe (after owner confirmation).
     */
    public WipeState confirmWipe(String deviceId, String wipeCode) {
        WipeState state = wipeStates.get(deviceId);
        if (state == null) {
            throw new IllegalArgumentException("No pending wipe for this device");
        }

        if (!hashWipeCode(wipeCode).equals(state.wipeCodeHash)) {
            throw new IllegalArgumentException("Invalid wipe confirmation code");
        }

        state.state = "WIPING";
        state.confirmedAt = Instant.now();

        // In production, this would send a wipe command to the device
        log.warn("Remote wipe CONFIRMED for device {}: data erasure in progress", deviceId);
        return state;
    }

    /**
     * Get wipe status.
     */
    public WipeState getWipeStatus(String deviceId) {
        return wipeStates.get(deviceId);
    }

    /**
     * Mark wipe as complete (acknowledged by device).
     */
    public WipeState markWipeComplete(String deviceId) {
        WipeState state = wipeStates.get(deviceId);
        if (state != null) {
            state.state = "COMPLETED";
            state.completedAt = Instant.now();
            wipeStates.put(deviceId, state);
            log.info("Remote wipe completed for device {}", deviceId);
        }
        return state;
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    /**
     * Calculate distance between two points using Haversine formula.
     */
    private double haversineDistance(double lat1, double lon1, double lat2, double lon2) {
        final double R = 6371000; // Earth radius in meters
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    private String hashWipeCode(String code) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(code.getBytes());
            return Base64.getEncoder().encodeToString(hash);
        } catch (Exception e) {
            return code;
        }
    }

    // ============================================================
    //  DTOs
    // ============================================================

    public static class DeviceLocation {
        public String deviceId;
        public double latitude;
        public double longitude;
        public double altitude;
        public double accuracy;
        public String address;
        public Instant updatedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "device_id", deviceId,
                    "latitude", latitude,
                    "longitude", longitude,
                    "altitude", altitude,
                    "accuracy", accuracy,
                    "address", address != null ? address : "",
                    "updated_at", updatedAt.toString()
            );
        }
    }

    public static class RingCommand {
        public String commandId;
        public String deviceId;
        public String commandType;
        public int durationSeconds;
        public int volume;
        public Instant issuedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "command_id", commandId,
                    "device_id", deviceId,
                    "command_type", commandType,
                    "duration_seconds", durationSeconds,
                    "volume", volume,
                    "issued_at", issuedAt.toString()
            );
        }
    }

    public static class LostModeState {
        public String deviceId;
        public boolean enabled;
        public String message;
        public String contactPhone;
        public String contactEmail;
        public Instant enabledAt;
        public Instant disabledAt;
        public double[] lastLocation;
        public Instant lastLocationUpdate;

        public Map<String, Object> toMap() {
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("device_id", deviceId);
            map.put("enabled", enabled);
            map.put("message", message != null ? message : "");
            map.put("contact_phone", contactPhone != null ? contactPhone : "");
            map.put("contact_email", contactEmail != null ? contactEmail : "");
            map.put("enabled_at", enabledAt != null ? enabledAt.toString() : null);
            map.put("disabled_at", disabledAt != null ? disabledAt.toString() : null);
            if (lastLocation != null) {
                map.put("last_location", Map.of("lat", lastLocation[0], "lon", lastLocation[1]));
            }
            map.put("last_location_update", lastLocationUpdate != null ? lastLocationUpdate.toString() : null);
            return map;
        }
    }

    public static class WipeState {
        public String deviceId;
        public String state; // PENDING_CONFIRMATION, WIPING, COMPLETED, FAILED
        public String wipeCodeHash;
        public String wipeCommandId;
        public Instant initiatedAt;
        public Instant confirmedAt;
        public Instant completedAt;

        public Map<String, Object> toMap() {
            return Map.of(
                    "device_id", deviceId,
                    "state", state,
                    "wipe_command_id", wipeCommandId,
                    "initiated_at", initiatedAt.toString(),
                    "confirmed_at", confirmedAt != null ? confirmedAt.toString() : null,
                    "completed_at", completedAt != null ? completedAt.toString() : null
            );
        }
    }
}
