package com.qoobot.qoocloud.inference.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * Hosted model entity for remote inference.
 */
@Entity
@Table(name = "inference_models")
public class InferenceModel {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private String modelId;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private String version;

    @Column(nullable = false)
    private String modelType;  // VISION, LANGUAGE, MULTIMODAL

    @Column(nullable = false)
    private String framework;  // ONNX, TensorRT, PyTorch, vLLM

    @Column(nullable = false)
    private String storagePath; // Object storage path

    @Column(nullable = false)
    private String state = "ACTIVE"; // ACTIVE, DEPRECATED, DISABLED

    private long sizeBytes;
    private String checksumSha256;

    private String gpuType;    // A100, H100, T4, etc.
    private int minGpuMemoryMb;
    private int maxBatchSize = 1;

    @Column(columnDefinition = "jsonb")
    private String supportedTasks; // JSON array of task types

    @Column(columnDefinition = "jsonb")
    private String config;         // Model-specific configuration

    private String createdBy;
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
    public String getModelId() { return modelId; }
    public void setModelId(String modelId) { this.modelId = modelId; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getVersion() { return version; }
    public void setVersion(String version) { this.version = version; }
    public String getModelType() { return modelType; }
    public void setModelType(String modelType) { this.modelType = modelType; }
    public String getFramework() { return framework; }
    public void setFramework(String framework) { this.framework = framework; }
    public String getStoragePath() { return storagePath; }
    public void setStoragePath(String storagePath) { this.storagePath = storagePath; }
    public String getState() { return state; }
    public void setState(String state) { this.state = state; }
    public long getSizeBytes() { return sizeBytes; }
    public void setSizeBytes(long sizeBytes) { this.sizeBytes = sizeBytes; }
    public String getChecksumSha256() { return checksumSha256; }
    public void setChecksumSha256(String checksumSha256) { this.checksumSha256 = checksumSha256; }
    public String getGpuType() { return gpuType; }
    public void setGpuType(String gpuType) { this.gpuType = gpuType; }
    public int getMinGpuMemoryMb() { return minGpuMemoryMb; }
    public void setMinGpuMemoryMb(int minGpuMemoryMb) { this.minGpuMemoryMb = minGpuMemoryMb; }
    public int getMaxBatchSize() { return maxBatchSize; }
    public void setMaxBatchSize(int maxBatchSize) { this.maxBatchSize = maxBatchSize; }
    public String getSupportedTasks() { return supportedTasks; }
    public void setSupportedTasks(String supportedTasks) { this.supportedTasks = supportedTasks; }
    public String getConfig() { return config; }
    public void setConfig(String config) { this.config = config; }
    public String getCreatedBy() { return createdBy; }
    public void setCreatedBy(String createdBy) { this.createdBy = createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
