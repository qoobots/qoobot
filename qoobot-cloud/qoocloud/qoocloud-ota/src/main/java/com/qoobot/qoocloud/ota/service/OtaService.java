package com.qoobot.qoocloud.ota.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;

/**
 * OTA (Over-The-Air) update service.
 * Handles firmware, model, and skill updates with incremental delivery,
 * canary/gray release, and automatic rollback.
 */
@Service
public class OtaService {

    private static final Logger log = LoggerFactory.getLogger(OtaService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // In-memory store (in production, use PostgreSQL)
    private final Map<String, UpdatePackage> packages = new HashMap<>();
    private final Map<String, UpdateCampaign> campaigns = new HashMap<>();

    public OtaService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Register an update package.
     */
    public UpdatePackage registerPackage(UpdatePackage pkg) {
        pkg.setCreatedAt(Instant.now());
        pkg.setState("DRAFT");
        packages.put(pkg.getPackageId(), pkg);
        log.info("OTA package registered: {} v{}", pkg.getPackageName(), pkg.getVersion());
        return pkg;
    }

    /**
     * Create an update campaign (canary/gray/full rollout).
     */
    public UpdateCampaign createCampaign(UpdateCampaign campaign) {
        campaign.setCampaignId(UUID.randomUUID().toString());
        campaign.setState("PENDING");
        campaign.setCreatedAt(Instant.now());
        campaigns.put(campaign.getCampaignId(), campaign);
        return campaign;
    }

    /**
     * Start a campaign rollout.
     */
    public void startRollout(String campaignId) {
        UpdateCampaign campaign = campaigns.get(campaignId);
        if (campaign == null) {
            throw new RuntimeException("Campaign not found: " + campaignId);
        }

        campaign.setState("ROLLING_OUT");
        campaign.setStartedAt(Instant.now());

        UpdatePackage pkg = packages.get(campaign.getPackageId());
        if (pkg != null) {
            pkg.setState("ROLLING_OUT");
        }

        log.info("OTA rollout started: campaign={}, package={} v{}, strategy={}",
                campaignId, campaign.getPackageId(),
                pkg != null ? pkg.getVersion() : "unknown",
                campaign.getRolloutStrategy());
    }

    /**
     * Check for available updates for a device.
     */
    public List<UpdatePackage> checkForUpdates(String deviceId, String currentFirmware,
                                                String currentQoobrain, List<String> currentSkills) {
        List<UpdatePackage> available = new ArrayList<>();

        for (UpdatePackage pkg : packages.values()) {
            if (!"ROLLING_OUT".equals(pkg.getState()) && !"ACTIVE".equals(pkg.getState())) {
                continue;
            }

            switch (pkg.getPackageType()) {
                case "FIRMWARE":
                    if (isNewerVersion(pkg.getVersion(), currentFirmware)) {
                        available.add(pkg);
                    }
                    break;
                case "QOOBRAIN":
                    if (isNewerVersion(pkg.getVersion(), currentQoobrain)) {
                        available.add(pkg);
                    }
                    break;
                case "SKILL":
                    // Check if skill is installed and has newer version
                    available.add(pkg);
                    break;
            }
        }

        return available;
    }

    /**
     * Generate an incremental (delta) update.
     */
    public DeltaUpdate generateDelta(String fromVersion, String toVersion, String packageId) {
        UpdatePackage pkg = packages.get(packageId);
        if (pkg == null) {
            throw new RuntimeException("Package not found: " + packageId);
        }

        // In production, compute binary diff between versions
        return new DeltaUpdate(
                packageId, fromVersion, toVersion,
                pkg.getSizeBytes() / 10, // Delta is typically ~10% of full size
                pkg.getChecksumSha256(),
                Instant.now()
        );
    }

    /**
     * Record update result from a device.
     */
    public void recordUpdateResult(String deviceId, String packageId,
                                    String fromVersion, String toVersion,
                                    boolean success, String errorMessage) {
        String key = "qoocloud:ota:results:" + packageId;
        String result = success ? "success" : "failure";

        redisTemplate.opsForHash().increment(key, result, 1);
        redisTemplate.opsForHash().increment(key, "total", 1);

        if (!success) {
            log.warn("OTA update failed: device={}, package={}, {}→{}, error={}",
                    deviceId, packageId, fromVersion, toVersion, errorMessage);

            // Auto-rollback if failure rate exceeds threshold
            checkAutoRollback(packageId);
        } else {
            log.info("OTA update success: device={}, package={}, {}→{}",
                    deviceId, packageId, fromVersion, toVersion);
        }
    }

    /**
     * Rollback a package to previous version.
     */
    public void rollback(String packageId) {
        UpdatePackage pkg = packages.get(packageId);
        if (pkg != null) {
            pkg.setState("ROLLED_BACK");
        }

        // Find and stop related campaigns
        for (UpdateCampaign campaign : campaigns.values()) {
            if (campaign.getPackageId().equals(packageId) &&
                    "ROLLING_OUT".equals(campaign.getState())) {
                campaign.setState("ROLLED_BACK");
            }
        }

        log.warn("OTA rollback initiated for package: {}", packageId);
    }

    /**
     * Get rollout statistics for a package.
     */
    public RolloutStats getRolloutStats(String packageId) {
        String key = "qoocloud:ota:results:" + packageId;
        Map<Object, Object> results = redisTemplate.opsForHash().entries(key);

        long total = Long.parseLong(results.getOrDefault("total", "0").toString());
        long success = Long.parseLong(results.getOrDefault("success", "0").toString());
        long failure = Long.parseLong(results.getOrDefault("failure", "0").toString());

        double successRate = total > 0 ? (double) success / total * 100 : 0;
        return new RolloutStats(packageId, total, success, failure, successRate);
    }

    private void checkAutoRollback(String packageId) {
        RolloutStats stats = getRolloutStats(packageId);
        // Auto-rollback if failure rate > 10% and at least 10 devices updated
        if (stats.total() >= 10 && stats.successRate() < 90.0) {
            log.error("Auto-rollback triggered: package={}, success_rate={}%",
                    packageId, stats.successRate());
            rollback(packageId);
        }
    }

    private boolean isNewerVersion(String newVersion, String currentVersion) {
        if (currentVersion == null) return true;
        String[] newParts = newVersion.replace("v", "").split("\\.");
        String[] curParts = currentVersion.replace("v", "").split("\\.");
        int len = Math.max(newParts.length, curParts.length);
        for (int i = 0; i < len; i++) {
            int n = i < newParts.length ? Integer.parseInt(newParts[i]) : 0;
            int c = i < curParts.length ? Integer.parseInt(curParts[i]) : 0;
            if (n != c) return n > c;
        }
        return false;
    }

    // --- DTOs ---

    public static class UpdatePackage {
        private String packageId;
        private String packageName;
        private String version;
        private String packageType; // FIRMWARE, QOOBRAIN, MODEL, SKILL
        private long sizeBytes;
        private String checksumSha256;
        private String downloadUrl;
        private String releaseNotes;
        private String state; // DRAFT, ACTIVE, ROLLING_OUT, ROLLED_BACK
        private Instant createdAt;

        public String getPackageId() { return packageId; }
        public void setPackageId(String packageId) { this.packageId = packageId; }
        public String getPackageName() { return packageName; }
        public void setPackageName(String packageName) { this.packageName = packageName; }
        public String getVersion() { return version; }
        public void setVersion(String version) { this.version = version; }
        public String getPackageType() { return packageType; }
        public void setPackageType(String packageType) { this.packageType = packageType; }
        public long getSizeBytes() { return sizeBytes; }
        public void setSizeBytes(long sizeBytes) { this.sizeBytes = sizeBytes; }
        public String getChecksumSha256() { return checksumSha256; }
        public void setChecksumSha256(String checksumSha256) { this.checksumSha256 = checksumSha256; }
        public String getDownloadUrl() { return downloadUrl; }
        public void setDownloadUrl(String downloadUrl) { this.downloadUrl = downloadUrl; }
        public String getReleaseNotes() { return releaseNotes; }
        public void setReleaseNotes(String releaseNotes) { this.releaseNotes = releaseNotes; }
        public String getState() { return state; }
        public void setState(String state) { this.state = state; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    }

    public static class UpdateCampaign {
        private String campaignId;
        private String packageId;
        private String rolloutStrategy; // CANARY, GRAY_10, GRAY_50, FULL
        private String state; // PENDING, ROLLING_OUT, COMPLETED, ROLLED_BACK
        private List<String> targetDeviceIds;
        private Instant createdAt;
        private Instant startedAt;

        public String getCampaignId() { return campaignId; }
        public void setCampaignId(String campaignId) { this.campaignId = campaignId; }
        public String getPackageId() { return packageId; }
        public void setPackageId(String packageId) { this.packageId = packageId; }
        public String getRolloutStrategy() { return rolloutStrategy; }
        public void setRolloutStrategy(String rolloutStrategy) { this.rolloutStrategy = rolloutStrategy; }
        public String getState() { return state; }
        public void setState(String state) { this.state = state; }
        public List<String> getTargetDeviceIds() { return targetDeviceIds; }
        public void setTargetDeviceIds(List<String> targetDeviceIds) { this.targetDeviceIds = targetDeviceIds; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
        public Instant getStartedAt() { return startedAt; }
        public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }
    }

    public record DeltaUpdate(
            String packageId,
            String fromVersion,
            String toVersion,
            long deltaSizeBytes,
            String checksum,
            Instant generatedAt
    ) {}

    public record RolloutStats(
            String packageId,
            long total,
            long success,
            long failure,
            double successRate
    ) {}
}
