package com.qoobot.qoocloud.device.service;

import com.qoobot.qoocloud.device.entity.Device;
import com.qoobot.qoocloud.device.repository.DeviceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

/**
 * Device management service.
 * Handles device registration, status monitoring, remote diagnostics,
 * configuration management, and device lifecycle.
 */
@Service
public class DeviceService {

    private static final Logger log = LoggerFactory.getLogger(DeviceService.class);
    private static final Duration DEVICE_OFFLINE_THRESHOLD = Duration.ofMinutes(5);

    private final DeviceRepository deviceRepository;
    private final RedisTemplate<String, String> redisTemplate;

    public DeviceService(DeviceRepository deviceRepository,
                         RedisTemplate<String, String> redisTemplate) {
        this.deviceRepository = deviceRepository;
        this.redisTemplate = redisTemplate;
    }

    /**
     * Register a new device in the cloud.
     */
    @Transactional
    public Device registerDevice(Device device) {
        device.setState("ACTIVATED");
        Device saved = deviceRepository.save(device);
        log.info("Device registered: {} ({})", saved.getDeviceId(), saved.getDeviceSerial());
        return saved;
    }

    /**
     * Device heartbeat — update online status and system metrics.
     */
    @Transactional
    public void heartbeat(String deviceId, String systemStatus, String ip,
                          Double lat, Double lng) {
        Optional<Device> deviceOpt = deviceRepository.findById(deviceId);
        if (deviceOpt.isEmpty()) {
            log.warn("Heartbeat from unknown device: {}", deviceId);
            return;
        }

        Device device = deviceOpt.get();
        device.setState("ONLINE");
        device.setLastSeenAt(Instant.now());
        device.setLastIp(ip);
        device.setSystemStatus(systemStatus);
        if (lat != null) device.setLastLatitude(lat);
        if (lng != null) device.setLastLongitude(lng);
        deviceRepository.save(device);

        // Update online status in Redis for fast queries
        redisTemplate.opsForValue().set(
                "qoocloud:device:online:" + deviceId, "1", Duration.ofMinutes(10));
    }

    /**
     * Get device by ID.
     */
    public Optional<Device> getDevice(String deviceId) {
        return deviceRepository.findById(deviceId);
    }

    /**
     * List all devices for a user.
     */
    public List<Device> getUserDevices(String userId) {
        return deviceRepository.findByBoundUserId(userId);
    }

    /**
     * List all devices with optional state filter.
     */
    public List<Device> listDevices(String state) {
        if (state != null) {
            return deviceRepository.findByState(state);
        }
        return deviceRepository.findAll();
    }

    /**
     * Check if a device is online.
     */
    public boolean isDeviceOnline(String deviceId) {
        return Boolean.TRUE.equals(redisTemplate.hasKey("qoocloud:device:online:" + deviceId));
    }

    /**
     * Get device count by state.
     */
    public long countByState(String state) {
        return deviceRepository.countByState(state);
    }

    /**
     * Run remote diagnostics on a device.
     */
    public DiagnosticsResult runDiagnostics(String deviceId) {
        Optional<Device> deviceOpt = deviceRepository.findById(deviceId);
        if (deviceOpt.isEmpty()) {
            return DiagnosticsResult.error("Device not found");
        }

        Device device = deviceOpt.get();
        boolean online = isDeviceOnline(deviceId);

        // In production, this would send a diagnostic command to the device
        // and collect results via the device's telemetry channel
        return new DiagnosticsResult(
                deviceId,
                device.getDeviceName(),
                online,
                online ? "Device is online and responding" : "Device is offline",
                device.getSystemStatus(),
                device.getFirmwareVersion(),
                device.getLastSeenAt()
        );
    }

    /**
     * Update device configuration.
     */
    @Transactional
    public Device updateConfig(String deviceId, String config) {
        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("Device not found: " + deviceId));
        device.setConfig(config);
        return deviceRepository.save(device);
    }

    /**
     * Lock a device remotely.
     */
    @Transactional
    public void lockDevice(String deviceId) {
        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("Device not found: " + deviceId));
        device.setState("LOCKED");
        deviceRepository.save(device);
        log.warn("Device locked: {}", deviceId);
    }

    /**
     * Wipe a device remotely.
     */
    @Transactional
    public void wipeDevice(String deviceId) {
        Device device = deviceRepository.findById(deviceId)
                .orElseThrow(() -> new RuntimeException("Device not found: " + deviceId));
        device.setState("WIPED");
        deviceRepository.save(device);
        log.warn("Device wiped: {}", deviceId);
    }

    /**
     * Mark offline devices.
     */
    public int markOfflineDevices() {
        Instant threshold = Instant.now().minus(DEVICE_OFFLINE_THRESHOLD);
        List<Device> staleDevices = deviceRepository.findByStateAndLastSeenAtBefore(
                "ONLINE", threshold);

        for (Device device : staleDevices) {
            device.setState("OFFLINE");
            deviceRepository.save(device);
            redisTemplate.delete("qoocloud:device:online:" + device.getDeviceId());
        }

        return staleDevices.size();
    }

    // --- DTO ---

    public record DiagnosticsResult(
            String deviceId,
            String deviceName,
            boolean online,
            String status,
            String systemStatus,
            String firmwareVersion,
            Instant lastSeenAt
    ) {
        public static DiagnosticsResult error(String message) {
            return new DiagnosticsResult(null, null, false, message, null, null, null);
        }
    }
}
