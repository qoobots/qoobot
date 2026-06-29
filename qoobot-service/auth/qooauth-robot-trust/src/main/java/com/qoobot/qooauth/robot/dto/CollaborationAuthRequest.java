package com.qoobot.qooauth.robot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CollaborationAuthRequest {

    @NotBlank(message = "Issuer device ID is required")
    private String issuerDeviceId;

    @NotBlank(message = "Recipient device ID is required")
    private String recipientDeviceId;

    private List<String> capabilities;

    /** Duration in seconds for the token validity. Defaults to 3600 (1 hour). */
    @Builder.Default
    private long ttlSeconds = 3600L;

    public Instant getExpiresAt() {
        return Instant.now().plusSeconds(ttlSeconds);
    }
}
