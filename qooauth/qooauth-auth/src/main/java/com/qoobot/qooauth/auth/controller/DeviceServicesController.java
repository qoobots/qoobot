package com.qoobot.qooauth.auth.controller;

import com.qoobot.qooauth.auth.service.DeviceAttestationService;
import com.qoobot.qooauth.auth.service.FindMyService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Unified REST controller for device services:
 * Find My QooBot, Device Attestation (RA-TLS), and MFQ Accessory Authentication.
 */
@RestController
@RequestMapping("/api/v1/auth/devices")
public class DeviceServicesController {

    private final FindMyService findMyService;
    private final DeviceAttestationService attestationService;

    public DeviceServicesController(FindMyService findMyService,
                                     DeviceAttestationService attestationService) {
        this.findMyService = findMyService;
        this.attestationService = attestationService;
    }

    // ---- Find My QooBot ----

    /**
     * Update device location.
     */
    @PostMapping("/{deviceId}/location")
    public ResponseEntity<Map<String, Object>> updateLocation(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> request) {
        double lat = ((Number) request.get("latitude")).doubleValue();
        double lon = ((Number) request.get("longitude")).doubleValue();
        double alt = ((Number) request.getOrDefault("altitude", 0)).doubleValue();
        double acc = ((Number) request.getOrDefault("accuracy", 0)).doubleValue();
        String address = (String) request.get("address");

        FindMyService.DeviceLocation loc = findMyService.updateLocation(deviceId, lat, lon, alt, acc, address);
        return ResponseEntity.ok(loc.toMap());
    }

    /**
     * Get device location.
     */
    @GetMapping("/{deviceId}/location")
    public ResponseEntity<Map<String, Object>> getLocation(@PathVariable String deviceId) {
        FindMyService.DeviceLocation loc = findMyService.getLocation(deviceId);
        if (loc == null) {
            return ResponseEntity.ok(Map.of("device_id", deviceId, "found", false));
        }
        Map<String, Object> result = new java.util.LinkedHashMap<>(loc.toMap());
        result.put("found", true);
        return ResponseEntity.ok(result);
    }

    /**
     * Check if device is nearby.
     */
    @GetMapping("/{deviceId}/nearby")
    public ResponseEntity<Map<String, Object>> checkNearby(
            @PathVariable String deviceId,
            @RequestParam double lat, @RequestParam double lon,
            @RequestParam(defaultValue = "100") double radiusMeters) {
        boolean nearby = findMyService.isNearby(deviceId, lat, lon, radiusMeters);
        return ResponseEntity.ok(Map.of("device_id", deviceId, "nearby", nearby, "radius_meters", radiusMeters));
    }

    /**
     * Trigger remote ring.
     */
    @PostMapping("/{deviceId}/ring")
    public ResponseEntity<Map<String, Object>> triggerRing(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> request) {
        int duration = ((Number) request.getOrDefault("duration_seconds", 30)).intValue();
        int volume = ((Number) request.getOrDefault("volume", 80)).intValue();

        FindMyService.RingCommand cmd = findMyService.triggerRing(deviceId, duration, volume);
        return ResponseEntity.ok(cmd.toMap());
    }

    /**
     * Stop ringing.
     */
    @DeleteMapping("/{deviceId}/ring")
    public ResponseEntity<Map<String, Object>> stopRing(@PathVariable String deviceId) {
        FindMyService.RingCommand cmd = findMyService.stopRing(deviceId);
        return ResponseEntity.ok(cmd.toMap());
    }

    /**
     * Enable Lost Mode.
     */
    @PostMapping("/{deviceId}/lost-mode")
    public ResponseEntity<Map<String, Object>> enableLostMode(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> request) {
        String message = request.getOrDefault("message", "This device has been marked as lost.");
        String phone = request.get("contact_phone");
        String email = request.get("contact_email");

        FindMyService.LostModeState state = findMyService.enableLostMode(deviceId, message, phone, email);
        return ResponseEntity.ok(state.toMap());
    }

    /**
     * Disable Lost Mode.
     */
    @DeleteMapping("/{deviceId}/lost-mode")
    public ResponseEntity<Map<String, Object>> disableLostMode(@PathVariable String deviceId) {
        FindMyService.LostModeState state = findMyService.disableLostMode(deviceId);
        if (state == null) {
            return ResponseEntity.ok(Map.of("device_id", deviceId, "enabled", false));
        }
        return ResponseEntity.ok(state.toMap());
    }

    /**
     * Get Lost Mode status.
     */
    @GetMapping("/{deviceId}/lost-mode")
    public ResponseEntity<Map<String, Object>> getLostModeStatus(@PathVariable String deviceId) {
        FindMyService.LostModeState state = findMyService.getLostModeStatus(deviceId);
        if (state == null) {
            return ResponseEntity.ok(Map.of("device_id", deviceId, "enabled", false));
        }
        return ResponseEntity.ok(state.toMap());
    }

    /**
     * Initiate remote wipe.
     */
    @PostMapping("/{deviceId}/wipe")
    public ResponseEntity<Map<String, Object>> initiateWipe(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> request) {
        String wipeCode = request.get("wipe_code");
        FindMyService.WipeState state = findMyService.initiateWipe(deviceId, wipeCode);
        return ResponseEntity.ok(state.toMap());
    }

    /**
     * Confirm remote wipe.
     */
    @PostMapping("/{deviceId}/wipe/confirm")
    public ResponseEntity<Map<String, Object>> confirmWipe(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> request) {
        String wipeCode = request.get("wipe_code");
        FindMyService.WipeState state = findMyService.confirmWipe(deviceId, wipeCode);
        return ResponseEntity.ok(state.toMap());
    }

    /**
     * Get wipe status.
     */
    @GetMapping("/{deviceId}/wipe")
    public ResponseEntity<Map<String, Object>> getWipeStatus(@PathVariable String deviceId) {
        FindMyService.WipeState state = findMyService.getWipeStatus(deviceId);
        if (state == null) {
            return ResponseEntity.ok(Map.of("device_id", deviceId, "state", "NONE"));
        }
        return ResponseEntity.ok(state.toMap());
    }

    // ---- Device Attestation (RA-TLS) ----

    /**
     * Generate attestation challenge.
     */
    @PostMapping("/{deviceId}/attestation/challenge")
    public ResponseEntity<Map<String, Object>> generateChallenge(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> request) {
        String verifierId = request.getOrDefault("verifier_id", "system");
        DeviceAttestationService.AttestationChallenge challenge =
                attestationService.generateChallenge(deviceId, verifierId);
        return ResponseEntity.ok(challenge.toMap());
    }

    /**
     * Verify attestation response.
     */
    @PostMapping("/{deviceId}/attestation/verify")
    public ResponseEntity<Map<String, Object>> verifyAttestation(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> request) {
        String challengeId = (String) request.get("challenge_id");
        String tpmQuote = (String) request.get("tpm_quote");
        String tpmSignature = (String) request.get("tpm_signature");
        String firmwareVersion = (String) request.get("firmware_version");

        @SuppressWarnings("unchecked")
        Map<String, Object> rawPcrs = (Map<String, Object>) request.getOrDefault("pcr_values", Map.of());
        Map<Integer, String> pcrValues = new java.util.HashMap<>();
        for (var entry : rawPcrs.entrySet()) {
            pcrValues.put(Integer.parseInt(entry.getKey()), (String) entry.getValue());
        }

        DeviceAttestationService.AttestationResult result =
                attestationService.verifyAttestation(challengeId, deviceId, pcrValues,
                        tpmQuote, tpmSignature, firmwareVersion);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Collect hardware fingerprint.
     */
    @PostMapping("/{deviceId}/fingerprint")
    public ResponseEntity<Map<String, Object>> collectFingerprint(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> hardwareInfo) {
        DeviceAttestationService.HardwareFingerprint fp =
                attestationService.collectFingerprint(deviceId, hardwareInfo);
        return ResponseEntity.ok(fp.toMap());
    }

    // ---- MFQ Accessory Authentication ----

    /**
     * Register MFQ accessory.
     */
    @PostMapping("/accessories")
    public ResponseEntity<Map<String, Object>> registerAccessory(@RequestBody Map<String, String> request) {
        String accessoryId = request.get("accessory_id");
        String manufacturerId = request.get("manufacturer_id");
        String modelId = request.get("model_id");
        String serialNumber = request.get("serial_number");
        String authChipId = request.get("auth_chip_id");
        String authChipPublicKey = request.get("auth_chip_public_key");

        DeviceAttestationService.MfqAccessory acc = attestationService.registerAccessory(
                accessoryId, manufacturerId, modelId, serialNumber, authChipId, authChipPublicKey);
        return ResponseEntity.ok(acc.toMap());
    }

    /**
     * Authenticate MFQ accessory.
     */
    @PostMapping("/accessories/{accessoryId}/authenticate")
    public ResponseEntity<Map<String, Object>> authenticateAccessory(
            @PathVariable String accessoryId,
            @RequestBody Map<String, String> request) {
        String challenge = request.get("challenge");
        String response = request.get("response");
        String signature = request.get("signature");

        DeviceAttestationService.AccessoryAuthResult result =
                attestationService.authenticateAccessory(accessoryId, challenge, response, signature);
        return ResponseEntity.ok(result.toMap());
    }

    /**
     * Get accessory info.
     */
    @GetMapping("/accessories/{accessoryId}")
    public ResponseEntity<Map<String, Object>> getAccessory(@PathVariable String accessoryId) {
        DeviceAttestationService.MfqAccessory acc = attestationService.getAccessory(accessoryId);
        if (acc == null) {
            return ResponseEntity.ok(Map.of("accessory_id", accessoryId, "found", false));
        }
        Map<String, Object> result = new java.util.LinkedHashMap<>(acc.toMap());
        result.put("found", true);
        return ResponseEntity.ok(result);
    }

    /**
     * Revoke MFQ accessory.
     */
    @DeleteMapping("/accessories/{accessoryId}")
    public ResponseEntity<Map<String, Object>> revokeAccessory(
            @PathVariable String accessoryId,
            @RequestParam(defaultValue = "security_concern") String reason) {
        attestationService.revokeAccessory(accessoryId, reason);
        return ResponseEntity.ok(Map.of("accessory_id", accessoryId, "status", "REVOKED"));
    }
}
