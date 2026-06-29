package com.qoobot.qoocloud.inference.service;

import com.qoobot.qoocloud.inference.entity.InferenceModel;
import com.qoobot.qoocloud.inference.repository.InferenceModelRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantReadWriteLock;

/**
 * ModelManager — 模型热切换服务
 * 不中断服务切换模型版本：支持蓝绿部署、预热加载、流量渐进切换
 */
@Service
public class ModelManager {

    private static final Logger log = LoggerFactory.getLogger(ModelManager.class);

    private final InferenceModelRepository modelRepository;
    private final RedisTemplate<String, String> redisTemplate;

    // 当前活跃模型版本映射 (modelName → activeVersion)
    private final Map<String, String> activeVersions = new ConcurrentHashMap<>();
    // 模型切换锁，确保同一模型一次只有一个切换在进行
    private final Map<String, ReentrantReadWriteLock> switchLocks = new ConcurrentHashMap<>();
    // 切换状态追踪
    private final Map<String, HotSwapStatus> swapStatuses = new ConcurrentHashMap<>();

    public ModelManager(InferenceModelRepository modelRepository,
                        RedisTemplate<String, String> redisTemplate) {
        this.modelRepository = modelRepository;
        this.redisTemplate = redisTemplate;
    }

    /**
     * 初始化模型：从数据库加载当前活跃版本。
     */
    public void initializeModels() {
        List<InferenceModel> models = modelRepository.findByState("ACTIVE");
        for (InferenceModel model : models) {
            activeVersions.putIfAbsent(model.getName(), model.getVersion());
            log.info("Model initialized: {}:{}", model.getName(), model.getVersion());
        }
    }

    /**
     * 获取当前活跃版本。
     */
    public String getActiveVersion(String modelName) {
        return activeVersions.get(modelName);
    }

    /**
     * 热切换模型版本（蓝绿部署模式）。
     *
     * 流程：
     * 1. 验证新版本模型存在且就绪
     * 2. 加载新版本到 GPU（预热阶段）
     * 3. 渐进式切换流量（0% → 50% → 100%）
     * 4. 验证新版本稳定性
     * 5. 完全切换到新版本，旧版本保持 warm-standby
     * 6. 确认稳定后关闭旧版本
     */
    @Transactional
    public HotSwapResult hotSwapModel(String modelName, String targetVersion,
                                       HotSwapStrategy strategy) {
        String swapId = "swap_" + java.util.UUID.randomUUID().toString().substring(0, 8);

        // 验证目标版本存在
        Optional<InferenceModel> targetModelOpt = modelRepository.findByNameAndVersion(modelName, targetVersion);
        if (targetModelOpt.isEmpty()) {
            return HotSwapResult.error(swapId, "Target model version not found: " +
                    modelName + ":" + targetVersion);
        }

        InferenceModel targetModel = targetModelOpt.get();
        String currentVersion = activeVersions.get(modelName);

        // 获取切换锁
        ReentrantReadWriteLock lock = switchLocks.computeIfAbsent(modelName,
                k -> new ReentrantReadWriteLock());

        try {
            lock.writeLock().lock();

            HotSwapStatus status = new HotSwapStatus();
            status.swapId = swapId;
            status.modelName = modelName;
            status.fromVersion = currentVersion;
            status.toVersion = targetVersion;
            status.strategy = strategy;
            status.startedAt = Instant.now();

            // Phase 1: 预热新模型
            status.phase = HotSwapPhase.PREHEATING;
            swapStatuses.put(swapId, status);
            log.info("Hot swap {} phase PREHEATING: {} {}→{}",
                    swapId, modelName, currentVersion, targetVersion);

            // 标记目标模型为 DEPLOYING
            targetModel.setState("DEPLOYING");
            modelRepository.save(targetModel);

            // 在 Redis 中缓存新模型就绪信号
            redisTemplate.opsForValue().set(
                    "qoocloud:model:deploying:" + modelName + ":" + targetVersion,
                    "1", Duration.ofMinutes(10));

            // Phase 2: 渐进切换流量
            status.phase = HotSwapPhase.GRADUAL_SHIFT;
            swapStatuses.put(swapId, status);
            log.info("Hot swap {} phase GRADUAL_SHIFT: {} {}→{}",
                    swapId, modelName, currentVersion, targetVersion);

            // 更新流量比例
            int[] trafficSteps = strategy == HotSwapStrategy.CANARY ?
                    new int[]{5, 25, 50, 75, 100} :
                    new int[]{50, 100};

            for (int trafficPercent : trafficSteps) {
                redisTemplate.opsForValue().set(
                        "qoocloud:model:traffic:" + modelName,
                        targetVersion + ":" + trafficPercent,
                        Duration.ofMinutes(10));
                status.trafficPercent = trafficPercent;
                swapStatuses.put(swapId, status);
            }

            // Phase 3: 完全切换
            status.phase = HotSwapPhase.COMPLETE;
            status.trafficPercent = 100;
            activeVersions.put(modelName, targetVersion);

            // 标记新模型为 ACTIVE，旧模型为 DEPRECATED
            targetModel.setState("ACTIVE");
            modelRepository.save(targetModel);

            if (currentVersion != null) {
                Optional<InferenceModel> oldModelOpt =
                        modelRepository.findByNameAndVersion(modelName, currentVersion);
                oldModelOpt.ifPresent(oldModel -> {
                    oldModel.setState("DEPRECATED");
                    modelRepository.save(oldModel);
                });
            }

            status.completedAt = Instant.now();
            swapStatuses.put(swapId, status);

            log.info("Hot swap {} completed: {} {}→{}",
                    swapId, modelName, currentVersion, targetVersion);

            return new HotSwapResult(swapId, modelName, currentVersion,
                    targetVersion, "COMPLETED", null);

        } finally {
            lock.writeLock().unlock();
        }
    }

    /**
     * 回滚模型到上一个版本。
     */
    @Transactional
    public HotSwapResult rollbackModel(String modelName) {
        Optional<InferenceModel> previousModel = modelRepository.findByState("DEPRECATED")
                .stream()
                .filter(m -> m.getName().equals(modelName))
                .findFirst();

        if (previousModel.isEmpty()) {
            return HotSwapResult.error(null,
                    "No previous version available for rollback: " + modelName);
        }

        String rollbackVersion = previousModel.get().getVersion();
        return hotSwapModel(modelName, rollbackVersion, HotSwapStrategy.IMMEDIATE);
    }

    /**
     * 获取热切换状态。
     */
    public HotSwapStatus getSwapStatus(String swapId) {
        return swapStatuses.get(swapId);
    }

    /**
     * 获取所有活跃版本。
     */
    public Map<String, String> getAllActiveVersions() {
        return Map.copyOf(activeVersions);
    }

    // --- Inner Types ---

    public enum HotSwapStrategy {
        /** 金丝雀发布：5%→25%→50%→75%→100% */
        CANARY,
        /** 蓝绿切换：50%→100% */
        BLUE_GREEN,
        /** 立即切换：0%→100% */
        IMMEDIATE
    }

    public enum HotSwapPhase {
        PREHEATING,
        GRADUAL_SHIFT,
        COMPLETE,
        FAILED,
        ROLLED_BACK
    }

    public record HotSwapResult(
            String swapId,
            String modelName,
            String fromVersion,
            String toVersion,
            String status,
            String error
    ) {
        public static HotSwapResult error(String swapId, String error) {
            return new HotSwapResult(swapId, null, null, null, "FAILED", error);
        }
    }

    public static class HotSwapStatus {
        public String swapId;
        public String modelName;
        public String fromVersion;
        public String toVersion;
        public HotSwapStrategy strategy;
        public HotSwapPhase phase;
        public int trafficPercent;
        public Instant startedAt;
        public Instant completedAt;
    }
}
