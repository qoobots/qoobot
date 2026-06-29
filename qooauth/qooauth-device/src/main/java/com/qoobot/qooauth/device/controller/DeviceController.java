package com.qoobot.qooauth.device.controller;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.dto.ApiResponse;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.device.dto.*;
import com.qoobot.qooauth.device.entity.Device;
import com.qoobot.qooauth.device.service.ActivationService;
import com.qoobot.qooauth.device.service.DeviceService;
import com.qoobot.qooauth.device.service.FindMyService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * REST controller for device management.
 * <p>
 * Base path: {@code /api/v1/devices}
 */
@RestController
@RequestMapping("/api/v1/devices")
public class DeviceController {

    private static final Logger log = LoggerFactory.getLogger(DeviceController.class);

    private final DeviceService deviceService;
    private final ActivationService activationService;
    private final FindMyService findMyService;

    public DeviceController(DeviceService deviceService,
                            ActivationService activationService,
                            FindMyService findMyService) {
        this.deviceService = deviceService;
        this.activationService = activationService;
        this.findMyService = findMyService;
    }

    // ========================================================================
    //  Activation
    // ========================================================================

    /**
     * POST /api/v1/devices/activate
     * <p>
     * Activate a new device. Public endpoint (no JWT required).
     * The client sends the device serial, hardware model, CSR, and optional
     * fingerprint data. The server validates the CSR, issues an X.509 device
     * certificate, and returns a one-time binding token.
     */
    @PostMapping("/activate")
    public ResponseEntity<ApiResponse<Map<String, Object>>> activate(
            @Valid @RequestBody DeviceActivateRequest request,
            @RequestHeader(value = "X-Forwarded-For", required = false) String forwardedFor) {

        String clientIp = forwardedFor != null ? forwardedFor.split(",")[0].trim() : "127.0.0.1";

        log.info("Device activation request: serial={}, model={}", request.getDeviceSerial(), request.getHardwareModel());

        String cpuId = null;
        String macAddress = null;
        String tpmEkHash = null;

        if (request.getDeviceFingerprint() != null) {
            cpuId = request.getDeviceFingerprint().getCpuId();
            macAddress = request.getDeviceFingerprint().getMacAddress();
            tpmEkHash = request.getDeviceFingerprint().getTpmEkHash();
        }

        ActivationService.ActivationResult result = activationService.activate(
                request.getDeviceSerial(),
                request.getHardwareModel(),
                request.getHardwareVersion(),
                request.getFirmwareVersion(),
                request.getCsr(),
                cpuId, macAddress, tpmEkHash,
                clientIp);

        Map<String, Object> response = Map.of(
                "device_id", result.getDeviceId(),
                "device_serial", result.getDeviceSerial(),
                "certificate", result.getCertificatePem(),
                "certificate_serial", result.getCertificateSerialNumber(),
                "certificate_expires_at", result.getCertificateExpiresAt().toString(),
                "binding_token", result.getBindingToken()
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(response));
    }

    // ========================================================================
    //  Binding
    // ========================================================================

    /**
     * POST /api/v1/devices/{deviceId}/bind
     * <p>
     * Bind a device to the authenticated user's account using the binding token
     * obtained during activation.
     */
    @PostMapping("/{deviceId}/bind")
    public ResponseEntity<ApiResponse<DeviceResponse>> bind(
            @PathVariable String deviceId,
            @Valid @RequestBody DeviceBindRequest request,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();

        // Validate binding token
        String tokenDeviceId = activationService.validateBindingToken(request.getBindingToken());

        if (!tokenDeviceId.equals(deviceId)) {
            throw new AuthException(ErrorCodes.DEVICE_ACTIVATION_STATE_INVALID,
                    "Binding token does not match the requested device");
        }

        log.info("Binding device {} to user {}", deviceId, userId);

        Device device = deviceService.bind(deviceId, userId, request.getDeviceName());

        // Update location if provided
        if (request.getLocation() != null && !request.getLocation().isBlank()) {
            deviceService.updateLocation(deviceId,
                    String.format("{\"label\":\"%s\"}", request.getLocation()));
        }

        // Consume the binding token (one-time use)
        activationService.consumeBindingToken(request.getBindingToken());

        return ResponseEntity.ok(ApiResponse.ok(DeviceResponse.from(device)));
    }

    /**
     * DELETE /api/v1/devices/{deviceId}/unbind
     * <p>
     * Unbind a device from the authenticated user's account.
     */
    @DeleteMapping("/{deviceId}/unbind")
    public ResponseEntity<ApiResponse<Void>> unbind(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.info("Unbinding device {} from user {}", deviceId, userId);

        deviceService.unbind(deviceId, userId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    // ========================================================================
    //  Lock / Lost Mode
    // ========================================================================

    /**
     * POST /api/v1/devices/{deviceId}/lock
     * <p>
     * Lock a device (activation lock or lost mode lock).
     */
    @PostMapping("/{deviceId}/lock")
    public ResponseEntity<ApiResponse<DeviceResponse>> lock(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.info("Locking device {} by user {}", deviceId, userId);

        Device device = deviceService.lock(deviceId, userId);
        return ResponseEntity.ok(ApiResponse.ok(DeviceResponse.from(device)));
    }

    // ========================================================================
    //  Remote wipe
    // ========================================================================

    /**
     * POST /api/v1/devices/{deviceId}/wipe
     * <p>
     * Trigger a remote wipe on the device.
     */
    @PostMapping("/{deviceId}/wipe")
    public ResponseEntity<ApiResponse<Map<String, String>>> wipe(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.info("Remote wipe requested for device {} by user {}", deviceId, userId);

        String commandId = findMyService.remoteWipe(deviceId, userId);

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "device_id", deviceId,
                "command_id", commandId,
                "status", "WIPE_COMMAND_SENT")));
    }

    // ========================================================================
    //  Location
    // ========================================================================

    /**
     * GET /api/v1/devices/{deviceId}/location
     * <p>
     * Get the last known location of a device.
     */
    @GetMapping("/{deviceId}/location")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getLocation(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.debug("Location requested for device {} by user {}", deviceId, userId);

        String locationJson = findMyService.getLastLocation(deviceId, userId);

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "device_id", deviceId,
                "last_location", locationJson != null ? locationJson : "null")));
    }

    // ========================================================================
    //  Guest mode
    // ========================================================================

    /**
     * POST /api/v1/devices/{deviceId}/guest
     * <p>
     * Enable guest mode on a device.
     */
    @PostMapping("/{deviceId}/guest")
    public ResponseEntity<ApiResponse<Map<String, String>>> enableGuest(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.info("Enabling guest mode for device {} by user {}", deviceId, userId);

        String guestToken = findMyService.enableGuestMode(deviceId, userId);

        return ResponseEntity.ok(ApiResponse.ok(Map.of(
                "device_id", deviceId,
                "guest_token", guestToken)));
    }

    /**
     * DELETE /api/v1/devices/{deviceId}/guest
     * <p>
     * Disable guest mode on a device.
     */
    @DeleteMapping("/{deviceId}/guest")
    public ResponseEntity<ApiResponse<Void>> disableGuest(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        log.info("Disabling guest mode for device {} by user {}", deviceId, userId);

        findMyService.disableGuestMode(deviceId, userId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    // ========================================================================
    //  Device queries
    // ========================================================================

    /**
     * GET /api/v1/devices
     * <p>
     * List all devices bound to the authenticated user.
     */
    @GetMapping
    public ResponseEntity<ApiResponse<List<DeviceResponse>>> listMyDevices(
            @AuthenticationPrincipal Jwt jwt) {

        String userId = jwt.getSubject();
        List<Device> devices = deviceService.findByOwner(userId);

        List<DeviceResponse> response = devices.stream()
                .map(DeviceResponse::from)
                .collect(Collectors.toList());

        return ResponseEntity.ok(ApiResponse.ok(response));
    }

    /**
     * GET /api/v1/devices/{deviceId}
     * <p>
     * Get details for a specific device.
     */
    @GetMapping("/{deviceId}")
    public ResponseEntity<ApiResponse<DeviceResponse>> getDevice(
            @PathVariable String deviceId,
            @AuthenticationPrincipal Jwt jwt) {

        Device device = deviceService.findByDeviceId(deviceId);

        // Users can only view their own devices
        String userId = jwt.getSubject();
        if (device.isBound() && !userId.equals(device.getBoundUserId())) {
            throw new AuthException(ErrorCodes.DEVICE_NOT_TRUSTED,
                    "You do not have access to this device");
        }

        return ResponseEntity.ok(ApiResponse.ok(DeviceResponse.from(device)));
    }

    // ========================================================================
    //  Exception handling
    // ========================================================================

    @ExceptionHandler(AuthException.class)
    public ResponseEntity<ApiResponse<Void>> handleAuthException(AuthException ex) {
        log.warn("Auth exception: code={}, message={}", ex.getErrorCode(), ex.getMessage());
        return ResponseEntity.status(mapHttpStatus(ex.getErrorCode()))
                .body(ApiResponse.error(ex.getErrorCode(), ex.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneralException(Exception ex) {
        log.error("Unhandled exception in DeviceController", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(ErrorCodes.INTERNAL_ERROR, "An unexpected error occurred"));
    }

    private HttpStatus mapHttpStatus(String errorCode) {
        if (errorCode == null) return HttpStatus.INTERNAL_SERVER_ERROR;
        return switch (errorCode) {
            case ErrorCodes.DEVICE_NOT_FOUND -> HttpStatus.NOT_FOUND;
            case ErrorCodes.DEVICE_ALREADY_BOUND -> HttpStatus.CONFLICT;
            case ErrorCodes.DEVICE_NOT_TRUSTED -> HttpStatus.FORBIDDEN;
            case ErrorCodes.DEVICE_CSR_INVALID -> HttpStatus.BAD_REQUEST;
            case ErrorCodes.DEVICE_ACTIVATION_EXPIRED -> HttpStatus.GONE;
            case ErrorCodes.DEVICE_CERT_NOT_FOUND -> HttpStatus.NOT_FOUND;
            default -> HttpStatus.BAD_REQUEST;
        };
    }
}
