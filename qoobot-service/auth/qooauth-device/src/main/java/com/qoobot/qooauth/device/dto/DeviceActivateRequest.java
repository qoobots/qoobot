package com.qoobot.qooauth.device.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for device activation request.
 * <p>
 * The client sends the factory device serial, hardware model, a PKCS#10 CSR
 * (PEM), and optional device fingerprint information.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceActivateRequest {

    /**
     * Factory-assigned device serial number (e.g. "QB-Home-V1-SN12345").
     */
    @NotBlank(message = "device_serial is required")
    @Size(min = 4, max = 64, message = "device_serial must be between 4 and 64 characters")
    private String deviceSerial;

    /**
     * Hardware model identifier (e.g. "QB-Home-V1", "QB-Nav-Pro").
     */
    @NotBlank(message = "hardware_model is required")
    @Size(max = 64, message = "hardware_model must be at most 64 characters")
    private String hardwareModel;

    /**
     * Hardware version string (optional).
     */
    @Size(max = 32)
    private String hardwareVersion;

    /**
     * Firmware version string (optional).
     */
    @Size(max = 32)
    private String firmwareVersion;

    /**
     * PKCS#10 Certificate Signing Request in PEM format.
     */
    @NotBlank(message = "csr is required")
    private String csr;

    /**
     * Device fingerprint data for hardware attestation.
     */
    @Valid
    private DeviceFingerprint deviceFingerprint;

    /**
     * Nested device fingerprint information.
     */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DeviceFingerprint {

        /** CPU ID or unique silicon identifier. */
        @Size(max = 128)
        private String cpuId;

        /** MAC address in colon-separated format (e.g. "AA:BB:CC:DD:EE:FF"). */
        @Pattern(regexp = "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", message = "mac_address must be in format AA:BB:CC:DD:EE:FF")
        private String macAddress;

        /** SHA-256 hash of the TPM endorsement key (optional, for TPM-backed devices). */
        @Size(max = 64)
        private String tpmEkHash;
    }
}
