package com.qoobot.qoocloud.inference.service;

import com.qoobot.qoocloud.inference.entity.InferenceModel;
import com.qoobot.qoocloud.inference.repository.InferenceModelRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Remote inference service.
 * Handles model hosting, inference scheduling, end-cloud hybrid routing,
 * and inference caching.
 */
@Service
public class InferenceService {

    private static final Logger log = LoggerFactory.getLogger(InferenceService.class);

    private final InferenceModelRepository modelRepository;
    private final RedisTemplate<String, String> redisTemplate;

    // Inference task queue per GPU type
    private final Map<String, Integer> gpuLoad = new ConcurrentHashMap<>();

    public InferenceService(InferenceModelRepository modelRepository,
                            RedisTemplate<String, String> redisTemplate) {
        this.modelRepository = modelRepository;
        this.redisTemplate = redisTemplate;
    }

    /**
     * Register a new model for hosting.
     */
    public InferenceModel registerModel(InferenceModel model) {
        model.setState("ACTIVE");
        return modelRepository.save(model);
    }

    /**
     * List all active models.
     */
    public List<InferenceModel> listModels() {
        return modelRepository.findByState("ACTIVE");
    }

    /**
     * Get a model by name and version.
     */
    public Optional<InferenceModel> getModel(String name, String version) {
        return modelRepository.findByNameAndVersion(name, version);
    }

    /**
     * Run inference synchronously.
     */
    public InferenceResponse infer(InferenceRequest request) {
        String taskId = UUID.randomUUID().toString();

        // Check cache for semantically similar requests
        String cacheKey = "qoocloud:inference:cache:" + hashRequest(request);
        String cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            log.debug("Inference cache hit for task {}", taskId);
            return new InferenceResponse(taskId, cached, 0, true);
        }

        // Find model
        Optional<InferenceModel> modelOpt = modelRepository.findByNameAndVersion(
                request.modelName(), request.modelVersion());
        if (modelOpt.isEmpty()) {
            return InferenceResponse.error(taskId, "Model not found: " +
                    request.modelName() + ":" + request.modelVersion());
        }

        // Check GPU availability
        InferenceModel model = modelOpt.get();
        int currentLoad = gpuLoad.getOrDefault(model.getGpuType(), 0);

        // Simulate inference (in production, dispatch to GPU worker)
        log.info("Running inference: model={}, task={}, gpu_load={}",
                model.getName(), taskId, currentLoad);

        // Update GPU load tracking
        gpuLoad.put(model.getGpuType(), currentLoad + 1);

        // In production, this would call Triton Inference Server / vLLM / ONNX Runtime
        String result = "[Inference result for " + request.modelName() + "]";

        // Cache result
        redisTemplate.opsForValue().set(cacheKey, result, Duration.ofMinutes(5));

        return new InferenceResponse(taskId, result, 150, false);
    }

    /**
     * Hybrid inference routing: decide whether to run on-device or in-cloud.
     */
    public RoutingDecision decideRouting(String taskType, long estimatedComplexity) {
        // Simple tasks → on-device (qoocore)
        // Complex tasks → cloud (qoocloud)
        if (estimatedComplexity < 100) {
            return RoutingDecision.ON_DEVICE;
        } else if (estimatedComplexity < 500) {
            return RoutingDecision.ON_DEVICE_PREFERRED;
        } else {
            return RoutingDecision.CLOUD_REQUIRED;
        }
    }

    /**
     * Get inference statistics.
     */
    public InferenceStats getStats() {
        long totalRequests = 0; // From metrics
        double avgLatency = 0;  // From metrics
        int activeModels = modelRepository.countByState("ACTIVE");
        return new InferenceStats(totalRequests, avgLatency, activeModels, gpuLoad);
    }

    private String hashRequest(InferenceRequest request) {
        return Integer.toHexString(request.hashCode());
    }

    // --- DTOs ---

    public record InferenceRequest(
            String modelName,
            String modelVersion,
            String input,
            Map<String, Object> parameters,
            boolean stream
    ) {}

    public record InferenceResponse(
            String taskId,
            String result,
            long latencyMs,
            boolean cacheHit,
            String error
    ) {
        public InferenceResponse(String taskId, String result, long latencyMs, boolean cacheHit) {
            this(taskId, result, latencyMs, cacheHit, null);
        }

        public static InferenceResponse error(String taskId, String error) {
            return new InferenceResponse(taskId, null, 0, false, error);
        }

        public boolean isSuccess() { return error == null; }
    }

    public enum RoutingDecision {
        ON_DEVICE,
        ON_DEVICE_PREFERRED,
        CLOUD_REQUIRED
    }

    public record InferenceStats(
            long totalRequests,
            double avgLatencyMs,
            int activeModels,
            Map<String, Integer> gpuLoad
    ) {}
}
