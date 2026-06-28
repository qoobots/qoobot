package com.qoobot.qoocloud.inference.controller;

import com.qoobot.qoocloud.inference.entity.InferenceModel;
import com.qoobot.qoocloud.inference.service.InferenceService;
import com.qoobot.qoocloud.inference.service.InferenceService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for remote inference.
 */
@RestController
@RequestMapping("/api/v1/inference")
public class InferenceController {

    private final InferenceService inferenceService;

    public InferenceController(InferenceService inferenceService) {
        this.inferenceService = inferenceService;
    }

    /**
     * Run inference.
     */
    @PostMapping
    public ResponseEntity<InferenceResponse> infer(@RequestBody Map<String, Object> body) {
        InferenceRequest request = new InferenceRequest(
                (String) body.get("model"),
                (String) body.getOrDefault("version", "latest").toString(),
                (String) body.get("input"),
                (Map<String, Object>) body.getOrDefault("parameters", Map.of()),
                (boolean) body.getOrDefault("stream", false)
        );

        InferenceResponse response = inferenceService.infer(request);
        if (response.isSuccess()) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.badRequest().body(response);
        }
    }

    /**
     * List hosted models.
     */
    @GetMapping("/models")
    public ResponseEntity<List<InferenceModel>> listModels() {
        return ResponseEntity.ok(inferenceService.listModels());
    }

    /**
     * Register a new model.
     */
    @PostMapping("/models")
    public ResponseEntity<InferenceModel> registerModel(@RequestBody InferenceModel model) {
        return ResponseEntity.ok(inferenceService.registerModel(model));
    }

    /**
     * Get inference routing decision.
     */
    @GetMapping("/routing")
    public ResponseEntity<RoutingDecision> getRouting(
            @RequestParam String taskType,
            @RequestParam(defaultValue = "0") long complexity) {
        return ResponseEntity.ok(inferenceService.decideRouting(taskType, complexity));
    }

    /**
     * Get inference statistics.
     */
    @GetMapping("/stats")
    public ResponseEntity<InferenceStats> getStats() {
        return ResponseEntity.ok(inferenceService.getStats());
    }
}
