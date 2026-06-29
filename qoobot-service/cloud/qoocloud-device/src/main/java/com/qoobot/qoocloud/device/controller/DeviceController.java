package com.qoobot.qoocloud.device.controller;

import com.qoobot.qoocloud.device.entity.Device;
import com.qoobot.qoocloud.device.service.DeviceGroupService;
import com.qoobot.qoocloud.device.service.DeviceService;
import com.qoobot.qoocloud.device.service.DeviceService.DiagnosticsResult;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * REST API for device management.
 */
@RestController
@RequestMapping("/api/v1/devices")
public class DeviceController {

    private final DeviceService deviceService;
    private final DeviceGroupService deviceGroupService;

    public DeviceController(DeviceService deviceService, DeviceGroupService deviceGroupService) {
        this.deviceService = deviceService;
        this.deviceGroupService = deviceGroupService;
    }

    /**
     * Register a new device.
     */
    @PostMapping
    public ResponseEntity<Device> register(@RequestBody Device device) {
        return ResponseEntity.ok(deviceService.registerDevice(device));
    }

    /**
     * Get device by ID.
     */
    @GetMapping("/{deviceId}")
    public ResponseEntity<Device> getDevice(@PathVariable String deviceId) {
        Optional<Device> device = deviceService.getDevice(deviceId);
        return device.map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * List devices (optionally filtered by state).
     */
    @GetMapping
    public ResponseEntity<List<Device>> listDevices(
            @RequestParam(required = false) String state) {
        return ResponseEntity.ok(deviceService.listDevices(state));
    }

    /**
     * Device heartbeat.
     */
    @PostMapping("/{deviceId}/heartbeat")
    public ResponseEntity<Void> heartbeat(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> body) {
        String systemStatus = (String) body.getOrDefault("systemStatus", "{}");
        String ip = (String) body.getOrDefault("ip", "unknown");
        Double lat = body.get("lat") != null ?
                ((Number) body.get("lat")).doubleValue() : null;
        Double lng = body.get("lng") != null ?
                ((Number) body.get("lng")).doubleValue() : null;

        deviceService.heartbeat(deviceId, systemStatus, ip, lat, lng);
        return ResponseEntity.ok().build();
    }

    /**
     * Check if device is online.
     */
    @GetMapping("/{deviceId}/online")
    public ResponseEntity<Map<String, Boolean>> isOnline(@PathVariable String deviceId) {
        return ResponseEntity.ok(Map.of("online", deviceService.isDeviceOnline(deviceId)));
    }

    /**
     * Run remote diagnostics.
     */
    @PostMapping("/{deviceId}/diagnostics")
    public ResponseEntity<DiagnosticsResult> runDiagnostics(@PathVariable String deviceId) {
        return ResponseEntity.ok(deviceService.runDiagnostics(deviceId));
    }

    /**
     * Update device configuration.
     */
    @PutMapping("/{deviceId}/config")
    public ResponseEntity<Device> updateConfig(
            @PathVariable String deviceId,
            @RequestBody Map<String, Object> config) {
        return ResponseEntity.ok(deviceService.updateConfig(deviceId, config.toString()));
    }

    /**
     * Lock device.
     */
    @PostMapping("/{deviceId}/lock")
    public ResponseEntity<Void> lockDevice(@PathVariable String deviceId) {
        deviceService.lockDevice(deviceId);
        return ResponseEntity.ok().build();
    }

    /**
     * Wipe device.
     */
    @PostMapping("/{deviceId}/wipe")
    public ResponseEntity<Void> wipeDevice(@PathVariable String deviceId) {
        deviceService.wipeDevice(deviceId);
        return ResponseEntity.ok().build();
    }

    /**
     * Get device statistics.
     */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Long>> getStats() {
        return ResponseEntity.ok(Map.of(
                "total", deviceService.listDevices(null).size(),
                "online", deviceService.countByState("ONLINE"),
                "offline", deviceService.countByState("OFFLINE"),
                "activated", deviceService.countByState("ACTIVATED")
        ));
    }

    // ================================================================
    // 设备分组
    // ================================================================

    /**
     * Create a device group.
     */
    @PostMapping("/groups")
    public ResponseEntity<DeviceGroupService.DeviceGroup> createGroup(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String description = (String) body.getOrDefault("description", "").toString();
        DeviceGroupService.GroupType type = DeviceGroupService.GroupType.valueOf(
                (String) body.getOrDefault("type", "STATIC"));
        @SuppressWarnings("unchecked")
        Map<String, String> filters = (Map<String, String>) body.getOrDefault("filters", Map.of());
        return ResponseEntity.ok(deviceGroupService.createGroup(name, description, type, filters));
    }

    /**
     * List all groups.
     */
    @GetMapping("/groups")
    public ResponseEntity<List<DeviceGroupService.DeviceGroup>> listGroups() {
        return ResponseEntity.ok(deviceGroupService.listGroups());
    }

    /**
     * Get group details.
     */
    @GetMapping("/groups/{groupId}")
    public ResponseEntity<DeviceGroupService.DeviceGroup> getGroup(
            @PathVariable String groupId) {
        return deviceGroupService.getGroup(groupId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Get devices in a group.
     */
    @GetMapping("/groups/{groupId}/devices")
    public ResponseEntity<List<Device>> getGroupDevices(@PathVariable String groupId) {
        return ResponseEntity.ok(deviceGroupService.getGroupDevices(groupId));
    }

    /**
     * Get group stats.
     */
    @GetMapping("/groups/{groupId}/stats")
    public ResponseEntity<DeviceGroupService.GroupStats> getGroupStats(
            @PathVariable String groupId) {
        return ResponseEntity.ok(deviceGroupService.getGroupStats(groupId));
    }

    /**
     * Add device to group.
     */
    @PostMapping("/groups/{groupId}/devices/{deviceId}")
    public ResponseEntity<Void> addDeviceToGroup(
            @PathVariable String groupId, @PathVariable String deviceId) {
        deviceGroupService.addDeviceToGroup(groupId, deviceId);
        return ResponseEntity.ok().build();
    }

    /**
     * Remove device from group.
     */
    @DeleteMapping("/groups/{groupId}/devices/{deviceId}")
    public ResponseEntity<Void> removeDeviceFromGroup(
            @PathVariable String groupId, @PathVariable String deviceId) {
        deviceGroupService.removeDeviceFromGroup(groupId, deviceId);
        return ResponseEntity.ok().build();
    }

    /**
     * Delete a group.
     */
    @DeleteMapping("/groups/{groupId}")
    public ResponseEntity<Void> deleteGroup(@PathVariable String groupId) {
        deviceGroupService.deleteGroup(groupId);
        return ResponseEntity.ok().build();
    }
}
