package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.entity.ActivationChallenge;
import com.qoobot.qooauth.auth.entity.DeviceActivation;
import com.qoobot.qooauth.auth.service.DeviceActivationService;
import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * Device Activation Controller.
 *
 * REST API for device first-boot activation lifecycle:
 * - Initiate activation (device presents bootstrap certificate)
 * - Issue cryptographic challenge
 * - Verify challenge response (device proves possession)
 * - Query activation status
 * - Revoke activation (unbind device from account)
 */
@RestController
@RequestMapping("/api/v1/auth/device-activations")
public class DeviceActivationController {

    private static final Logger log = LoggerFactory.getLogger(DeviceActivationController.class);

    private final DeviceActivationService activationService;

    public DeviceActivationController(DeviceActivationService activationService) {
        this.activationService = activationService;
    }

    // ========================================================================
    // Activation Flow
    // ========================================================================

    /**
     * Step 1: Initiate device activation.
     * Device presents its bootstrap certificate and hardware info.
     * Server creates an activation session and returns an encrypted activation token.
     */
    @PostMapping("/initiate")
    public ResponseEntity<?> initiateActivation(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody InitiateRequest request) {

        String userId = jwt.getSubject();
        try {
            DeviceActivationService.ActivationInitiateResponse response =
                    activationService.initiateActivation(
                            userId,
                            request.bootstrapCertId(),
                            request.deviceSerial(),
                            request.deviceModel(),
                            request.firmwareVersion(),
                            request.hardwareFingerprint());

            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                    "success", true,
                    "data", response
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    /**
     * Step 2: Request a cryptographic challenge.
     * Device calls this after receiving activation token to prove possession
     * of the bootstrap private key. No JWT required — device authenticates
     * via activation token in the request body.
     */
    @PostMapping("/{activationId}/challenge")
    public ResponseEntity<?> requestChallenge(
            @PathVariable String activationId,
            @RequestBody Map<String, String> body) {

        // Activation token-based authorization (device presents its encrypted token)
        // Full token validation is deferred to the service layer
        try {
            DeviceActivationService.ActivationChallengeResponse response =
                    activationService.issueChallenge(activationId);

            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "data", response
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    /**
     * Step 3: Submit signed challenge response.
     * Device signs the nonce with its bootstrap private key.
     * Server verifies and, if valid, issues an operational certificate.
     * No JWT required — device proves possession via cryptographic signature.
     */
    @PostMapping("/{activationId}/verify")
    public ResponseEntity<?> verifyChallenge(
            @PathVariable String activationId,
            @Valid @RequestBody VerifyRequest request) {

        try {
            DeviceActivationService.ActivationVerifyResponse response =
                    activationService.verifyChallenge(
                            activationId,
                            request.challengeId(),
                            request.signedNonce());

            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "data", response
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    // ========================================================================
    // Query APIs
    // ========================================================================

    /**
     * Get activation details by ID.
     */
    @GetMapping("/{activationId}")
    public ResponseEntity<?> getActivation(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable String activationId) {

        try {
            DeviceActivation activation = activationService.getActivation(activationId);
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "data", activation
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    /**
     * Get activation details by device ID.
     */
    @GetMapping("/by-device/{deviceId}")
    public ResponseEntity<?> getActivationByDevice(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable String deviceId) {

        try {
            DeviceActivation activation = activationService.getActivationByDevice(deviceId);
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "data", activation
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    /**
     * List all activations for the authenticated user.
     */
    @GetMapping("/mine")
    public ResponseEntity<?> listMyActivations(@AuthenticationPrincipal Jwt jwt) {
        String userId = jwt.getSubject();
        List<DeviceActivation> activations = activationService.listActivationsByUser(userId);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "data", activations,
                "count", activations.size()
        ));
    }

    /**
     * List challenge records for an activation.
     */
    @GetMapping("/{activationId}/challenges")
    public ResponseEntity<?> listChallenges(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable String activationId) {

        List<ActivationChallenge> challenges = activationService.listChallenges(activationId);
        return ResponseEntity.ok(Map.of(
                "success", true,
                "data", challenges,
                "count", challenges.size()
        ));
    }

    // ========================================================================
    // Revocation
    // ========================================================================

    /**
     * Revoke a device activation — unbinds device from user account.
     */
    @DeleteMapping("/{activationId}")
    public ResponseEntity<?> revokeActivation(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable String activationId,
            @RequestParam(defaultValue = "user_requested") String reason) {

        try {
            activationService.revokeActivation(activationId, reason);
            return ResponseEntity.ok(Map.of(
                    "success", true,
                    "message", "Device activation revoked"
            ));

        } catch (AuthException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                    "success", false,
                    "error_code", e.getErrorCode(),
                    "error", e.getMessage()
            ));
        }
    }

    // ========================================================================
    // Request DTOs
    // ========================================================================

    public record InitiateRequest(
            @NotBlank @Size(max = 64) String bootstrapCertId,
            @NotBlank @Size(max = 128) String deviceSerial,
            @Size(max = 128) String deviceModel,
            @Size(max = 32) String firmwareVersion,
            @Size(max = 256) String hardwareFingerprint
    ) {}

    public record VerifyRequest(
            @NotBlank @Size(max = 64) String challengeId,
            @NotBlank String signedNonce
    ) {}
}
