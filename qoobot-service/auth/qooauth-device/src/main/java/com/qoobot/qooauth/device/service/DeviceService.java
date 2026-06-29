package com.qoobot.qooauth.device.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.enums.DeviceState;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.util.IdGenerator;
import com.qoobot.qooauth.device.entity.Device;
import com.qoobot.qooauth.device.repository.DeviceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Business logic for device lifecycle management.
 * <p>
 * Handles device registration, activation, binding/unbinding,
 * status transitions, and query operations.
 */
@Service
@Transactional
public class DeviceService {

    private static final Logger log = LoggerFactory.getLogger(DeviceService.class);

    private final DeviceRepository deviceRepository;

    public DeviceService(DeviceRepository deviceRepository) {
        this.deviceRepository = deviceRepository;
    }

    /**
     * Register a new device in the system.
     * <p>
     * Generates a unique device_id, sets the initial state to ACTIVATED,
     * and persists the device record.
     *
     * @param deviceSerial  factory serial number
     * @param hardwareModel hardware model identifier
     * @param hardwareVersion optional hardware version
     * @param firmwareVersion optional firmware version
     * @param certificateSn  issued certificate serial number
     * @param certificatePem PEM-encoded device certificate
     * @param certificateExpiresAt certificate expiration timestamp
     * @param cpuId      optional CPU identifier
     * @param macAddress optional MAC address
     * @param tpmEkHash  optional TPM endorsement key hash
     * @param lastIp     client IP address
     * @return the persisted Device entity
     */
    public Device register(String deviceSerial, String hardwareModel,
                           String hardwareVersion, String firmwareVersion,
                           String certificateSn, String certificatePem,
                           OffsetDateTime certificateExpiresAt,
                           String cpuId, String macAddress, String tpmEkHash,
                           String lastIp) {

        if (deviceRepository.existsByDeviceSerial(deviceSerial)) {
            log.warn("Device serial {} already registered", deviceSerial);
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND,
                    "Device with serial " + deviceSerial + " is already registered");
        }

        Device device = Device.builder()
                .deviceId(IdGenerator.generateDeviceId())
                .deviceSerial(deviceSerial)
                .hardwareModel(hardwareModel)
                .hardwareVersion(hardwareVersion)
                .firmwareVersion(firmwareVersion)
                .certificateSn(certificateSn)
                .certificatePem(certificatePem)
                .certificateExpiresAt(certificateExpiresAt)
                .state(DeviceState.ACTIVATED)
                .cpuId(cpuId)
                .macAddress(macAddress)
                .tpmEkHash(tpmEkHash)
                .lastIp(lastIp)
                .lastSeenAt(OffsetDateTime.now())
                .build();

        Device saved = deviceRepository.save(device);
        log.info("Device registered: id={}, serial={}, model={}", saved.getDeviceId(), deviceSerial, hardwareModel);
        return saved;
    }

    /**
     * Bind a device to a user account.
     *
     * @param deviceId   the device ID
     * @param userId     the user ID to bind to
     * @param deviceName user-assigned device name
     */
    public Device bind(String deviceId, String userId, String deviceName) {
        Device device = findByDeviceId(deviceId);

        if (device.isBound()) {
            log.warn("Device {} is already bound to user {}", deviceId, device.getBoundUserId());
            throw new AuthException(ErrorCodes.DEVICE_ALREADY_BOUND,
                    "Device is already bound to a user");
        }

        device.setBoundUserId(userId);
        device.setDeviceName(deviceName);
        device.setBoundAt(OffsetDateTime.now());
        device.setState(DeviceState.BOUND);

        Device saved = deviceRepository.save(device);
        log.info("Device {} bound to user {}", deviceId, userId);
        return saved;
    }

    /**
     * Unbind a device from its owner.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user (must be the bound user)
     */
    public void unbind(String deviceId, String userId) {
        Device device = findByDeviceId(deviceId);

        if (!device.isBound()) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_FOUND,
                    "Device is not bound to any user");
        }

        if (!userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "Only the device owner can unbind this device");
        }

        device.setBoundUserId(null);
        device.setDeviceName(null);
        device.setBoundAt(null);
        device.setState(DeviceState.ACTIVATED);

        deviceRepository.save(device);
        log.info("Device {} unbound from user {}", deviceId, userId);
    }

    /**
     * Lock a device (activation lock / lost mode).
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     */
    public Device lock(String deviceId, String userId) {
        Device device = findByDeviceId(deviceId);
        validateOwnership(device, userId);

        device.setState(DeviceState.LOCKED);
        Device saved = deviceRepository.save(device);
        log.info("Device {} locked by user {}", deviceId, userId);
        return saved;
    }

    /**
     * Mark a device as lost.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     */
    public Device markLost(String deviceId, String userId) {
        Device device = findByDeviceId(deviceId);
        validateOwnership(device, userId);

        device.setState(DeviceState.LOST);
        Device saved = deviceRepository.save(device);
        log.info("Device {} marked as lost by user {}", deviceId, userId);
        return saved;
    }

    /**
     * Remote wipe a device.
     *
     * @param deviceId the device ID
     * @param userId   the requesting user
     */
    public Device wipe(String deviceId, String userId) {
        Device device = findByDeviceId(deviceId);
        validateOwnership(device, userId);

        device.setState(DeviceState.WIPED);
        Device saved = deviceRepository.save(device);
        log.info("Device {} wiped by user {}", deviceId, userId);
        return saved;
    }

    /**
     * Update the device's last-seen timestamp and IP.
     */
    public void updateLastSeen(String deviceId, String ipAddress) {
        deviceRepository.findById(deviceId).ifPresent(device -> {
            device.setLastSeenAt(OffsetDateTime.now());
            if (ipAddress != null) {
                device.setLastIp(ipAddress);
            }
            deviceRepository.save(device);
        });
    }

    /**
     * Update the device's location.
     */
    public void updateLocation(String deviceId, String locationJson) {
        deviceRepository.findById(deviceId).ifPresent(device -> {
            device.setLastLocation(locationJson);
            device.setLastSeenAt(OffsetDateTime.now());
            deviceRepository.save(device);
        });
    }

    /**
     * Update device firmware version.
     */
    public void updateFirmwareVersion(String deviceId, String firmwareVersion) {
        deviceRepository.findById(deviceId).ifPresent(device -> {
            device.setFirmwareVersion(firmwareVersion);
            deviceRepository.save(device);
        });
    }

    // --- Query methods ---

    /**
     * Find a device by its ID, throwing if not found.
     */
    public Device findByDeviceId(String deviceId) {
        return deviceRepository.findById(deviceId)
                .orElseThrow(() -> new AuthException(ErrorCodes.DEVICE_NOT_FOUND,
                        "Device not found: " + deviceId));
    }

    /**
     * Find a device by its serial number.
     */
    public Optional<Device> findByDeviceSerial(String deviceSerial) {
        return deviceRepository.findByDeviceSerial(deviceSerial);
    }

    /**
     * Find all devices bound to a user.
     */
    public List<Device> findByOwner(String userId) {
        return deviceRepository.findByBoundUserId(userId);
    }

    /**
     * Find all active (non-wiped) devices bound to a user.
     */
    public List<Device> findActiveByOwner(String userId) {
        return deviceRepository.findActiveByBoundUserId(userId);
    }

    /**
     * Find devices by state.
     */
    public List<Device> findByState(DeviceState state) {
        return deviceRepository.findByState(state);
    }

    // --- Internal helpers ---

    private void validateOwnership(Device device, String userId) {
        if (!device.isBound() || !userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "User does not own this device");
        }
    }
}
