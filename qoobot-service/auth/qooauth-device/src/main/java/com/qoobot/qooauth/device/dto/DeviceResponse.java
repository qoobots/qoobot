package com.qoobot.qooauth.device.dto;

import com.qoobot.qooauth.common.enums.DeviceState;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * Response DTO for device information.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceResponse {

    private String deviceId;
    private String deviceSerial;
    private String hardwareModel;
    private String hardwareVersion;
    private String firmwareVersion;
    private String certificateSn;
    private OffsetDateTime certificateExpiresAt;
    private String boundUserId;
    private String deviceName;
    private OffsetDateTime boundAt;
    private DeviceState state;
    private String cpuId;
    private String macAddress;
    private String lastIp;
    private String lastLocation;
    private OffsetDateTime lastSeenAt;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    /**
     * Create a DeviceResponse from a Device entity.
     */
    public static DeviceResponse from(com.qoobot.qooauth.device.entity.Device device) {
        return DeviceResponse.builder()
                .deviceId(device.getDeviceId())
                .deviceSerial(device.getDeviceSerial())
                .hardwareModel(device.getHardwareModel())
                .hardwareVersion(device.getHardwareVersion())
                .firmwareVersion(device.getFirmwareVersion())
                .certificateSn(device.getCertificateSn())
                .certificateExpiresAt(device.getCertificateExpiresAt())
                .boundUserId(device.getBoundUserId())
                .deviceName(device.getDeviceName())
                .boundAt(device.getBoundAt())
                .state(device.getState())
                .cpuId(device.getCpuId())
                .macAddress(device.getMacAddress())
                .lastIp(device.getLastIp())
                .lastLocation(device.getLastLocation())
                .lastSeenAt(device.getLastSeenAt())
                .createdAt(device.getCreatedAt())
                .updatedAt(device.getUpdatedAt())
                .build();
    }
}
