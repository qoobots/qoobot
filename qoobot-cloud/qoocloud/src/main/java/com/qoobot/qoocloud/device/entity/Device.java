package com.qoobot.qoocloud.device.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "cloud_devices")
public class Device {

    @Id
    private String deviceId;

    @Column(nullable = false, unique = true)
    private String deviceSerial;

    @Column(nullable = false)
    private String hardwareModel;

    private String hardwareVersion;
    private String firmwareVersion;
    private String qoobrainVersion;

    private String boundUserId;
    private String deviceName;

    @Column(nullable = false)
    private String state = "ACTIVATED"; // ACTIVATED, BOUND, ONLINE, OFFLINE, LOCKED, WIPED

    private String lastIp;
    private Double lastLatitude;
    private Double lastLongitude;

    @Column(columnDefinition = "jsonb")
    private String systemStatus; // CPU, memory, disk, battery

    @Column(columnDefinition = "jsonb")
    private String config; // Device-specific configuration

    @Column(columnDefinition = "jsonb")
    private String capabilities; // What this device can do

    private Instant lastSeenAt;
    private Instant createdAt;
    private Instant updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = Instant.now();
        updatedAt = Instant.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = Instant.now();
    }

    // Getters and setters
    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }
    public String getDeviceSerial() { return deviceSerial; }
    public void setDeviceSerial(String deviceSerial) { this.deviceSerial = deviceSerial; }
    public String getHardwareModel() { return hardwareModel; }
    public void setHardwareModel(String hardwareModel) { this.hardwareModel = hardwareModel; }
    public String getHardwareVersion() { return hardwareVersion; }
    public void setHardwareVersion(String hardwareVersion) { this.hardwareVersion = hardwareVersion; }
    public String getFirmwareVersion() { return firmwareVersion; }
    public void setFirmwareVersion(String firmwareVersion) { this.firmwareVersion = firmwareVersion; }
    public String getQoobrainVersion() { return qoobrainVersion; }
    public void setQoobrainVersion(String qoobrainVersion) { this.qoobrainVersion = qoobrainVersion; }
    public String getBoundUserId() { return boundUserId; }
    public void setBoundUserId(String boundUserId) { this.boundUserId = boundUserId; }
    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public String getLastIp() { return lastIp; }
    public void setLastIp(String lastIp) { this.lastIp = lastIp; }
    public Double getLastLatitude() { return lastLatitude; }
    public void setLastLatitude(Double lastLatitude) { this.lastLatitude = lastLatitude; }
    public Double getLastLongitude() { return lastLongitude; }
    public void setLastLongitude(Double lastLongitude) { this.lastLongitude = lastLongitude; }
    public String getSystemStatus() { return systemStatus; }
    public void setSystemStatus(String systemStatus) { this.systemStatus = systemStatus; }
    public String getConfig() { return config; }
    public void setConfig(String config) { this.config = config; }
    public String getCapabilities() { return capabilities; }
    public void setCapabilities(String capabilities) { this.capabilities = capabilities; }
    public Instant getLastSeenAt() { return lastSeenAt; }
    public void setLastSeenAt(Instant lastSeenAt) { this.lastSeenAt = lastSeenAt; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
