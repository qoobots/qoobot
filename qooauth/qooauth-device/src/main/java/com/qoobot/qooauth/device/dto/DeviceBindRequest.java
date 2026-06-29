package com.qoobot.qooauth.device.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for binding a device to a user account.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DeviceBindRequest {

    /**
     * One-time binding token issued during activation.
     */
    @NotBlank(message = "binding_token is required")
    private String bindingToken;

    /**
     * User-assigned device name (e.g. "Living Room Robot", "Office Assistant").
     */
    @NotBlank(message = "device_name is required")
    @Size(min = 1, max = 64, message = "device_name must be between 1 and 64 characters")
    private String deviceName;

    /**
     * Optional location description (e.g. "Home — Kitchen").
     */
    @Size(max = 256)
    private String location;
}
