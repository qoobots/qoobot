package com.qoobot.qoocloud.ota.controller;

import com.qoobot.qoocloud.ota.service.OtaService;
import com.qoobot.qoocloud.ota.service.OtaService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for OTA update management.
 */
@RestController
@RequestMapping("/api/v1/ota")
public class OtaController {

    private final OtaService otaService;

    public OtaController(OtaService otaService) {
        this.otaService = otaService;
    }

    /**
     * Register an update package.
     */
    @PostMapping("/packages")
    public ResponseEntity<UpdatePackage> registerPackage(@RequestBody UpdatePackage pkg) {
        return ResponseEntity.ok(otaService.registerPackage(pkg));
    }

    /**
     * Create an update campaign.
     */
    @PostMapping("/campaigns")
    public ResponseEntity<UpdateCampaign> createCampaign(@RequestBody UpdateCampaign campaign) {
        return ResponseEntity.ok(otaService.createCampaign(campaign));
    }

    /**
     * Start a campaign rollout.
     */
    @PostMapping("/campaigns/{campaignId}/start")
    public ResponseEntity<Void> startRollout(@PathVariable String campaignId) {
        otaService.startRollout(campaignId);
        return ResponseEntity.ok().build();
    }

    /**
     * Check for available updates for a device.
     */
    @GetMapping("/check")
    public ResponseEntity<List<UpdatePackage>> checkForUpdates(
            @RequestParam String deviceId,
            @RequestParam(required = false) String firmware,
            @RequestParam(required = false) String qoobrain) {
        return ResponseEntity.ok(
                otaService.checkForUpdates(deviceId, firmware, qoobrain, List.of()));
    }

    /**
     * Generate delta update.
     */
    @GetMapping("/delta")
    public ResponseEntity<DeltaUpdate> generateDelta(
            @RequestParam String fromVersion,
            @RequestParam String toVersion,
            @RequestParam String packageId) {
        return ResponseEntity.ok(otaService.generateDelta(fromVersion, toVersion, packageId));
    }

    /**
     * Record update result from device.
     */
    @PostMapping("/results")
    public ResponseEntity<Void> recordResult(@RequestBody Map<String, Object> body) {
        otaService.recordUpdateResult(
                (String) body.get("deviceId"),
                (String) body.get("packageId"),
                (String) body.get("fromVersion"),
                (String) body.get("toVersion"),
                (boolean) body.getOrDefault("success", false),
                (String) body.getOrDefault("error", "")
        );
        return ResponseEntity.ok().build();
    }

    /**
     * Rollback a package.
     */
    @PostMapping("/packages/{packageId}/rollback")
    public ResponseEntity<Void> rollback(@PathVariable String packageId) {
        otaService.rollback(packageId);
        return ResponseEntity.ok().build();
    }

    /**
     * Get rollout statistics.
     */
    @GetMapping("/packages/{packageId}/stats")
    public ResponseEntity<RolloutStats> getStats(@PathVariable String packageId) {
        return ResponseEntity.ok(otaService.getRolloutStats(packageId));
    }
}
